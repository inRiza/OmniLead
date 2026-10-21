"""Webhook kanal masuk: WhatsApp, Instagram, Facebook Page, dan push Gmail.

Aturan:
- Verifikasi Meta: `hub.mode=subscribe` + `hub.verify_token` -> balas `hub.challenge`.
- Setiap POST Meta wajib membawa `X-Hub-Signature-256` (HMAC-SHA256 isi mentah
  dengan app secret). Tanpa signature valid -> 403. App secret kosong -> 403.
- Balas 200 secepatnya; event diproses di background. Dedup berdasarkan ID
  pesan ada di `IngestService` (Meta mengulang kiriman hingga 36 jam).
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from omnilead.api.deps import get_ingest, get_registry, get_accounts, ingest_for_workspace, registry_for_workspace
from omnilead.config import Settings, get_settings
from omnilead.connectors.base import ConnectorError
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.models import Channel, EventIn, Sender

log = logging.getLogger("omnilead.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _verify_challenge(settings: Settings, mode: str | None, token: str | None, challenge: str | None):
    if (
        mode == "subscribe"
        and settings.meta_verify_token
        and token
        and hmac.compare_digest(token, settings.meta_verify_token)
    ):
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Verifikasi webhook gagal")


def _ts(value) -> datetime | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n > 10_000_000_000:  # milidetik (Instagram)
        n //= 1000
    return datetime.fromtimestamp(n, tz=timezone.utc)


def parse_whatsapp(payload: dict) -> list[EventIn]:
    events: list[EventIn] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {
                c.get("wa_id"): (c.get("profile") or {}).get("name")
                for c in value.get("contacts", [])
            }
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue  # media/lokasi belum didukung
                sender = msg.get("from", "")
                events.append(EventIn(
                    channel=Channel.WHATSAPP, kind="message", external_id=msg["id"],
                    sender=Sender(handle=sender, phone=sender, name=names.get(sender)),
                    text=(msg.get("text") or {}).get("body", ""),
                    ts=_ts(msg.get("timestamp")),
                ))
    return [e for e in events if e.text.strip()]


def parse_instagram(payload: dict) -> list[EventIn]:
    events: list[EventIn] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            v = change.get("value", {})
            who = v.get("from", {})
            if not v.get("id") or not v.get("text"):
                continue
            events.append(EventIn(
                channel=Channel.INSTAGRAM, kind="comment", external_id=v["id"],
                sender=Sender(handle=who.get("username") or who.get("id", "")),
                text=v["text"], post_ref=(v.get("media") or {}).get("id"),
                comment_ref=v["id"], ts=_ts(entry.get("time")),
            ))
        for m in entry.get("messaging", []):
            msg = m.get("message") or {}
            if msg.get("is_echo") or not msg.get("text") or not msg.get("mid"):
                continue
            events.append(EventIn(
                channel=Channel.INSTAGRAM, kind="dm", external_id=msg["mid"],
                sender=Sender(handle=m.get("sender", {}).get("id", "")),
                text=msg["text"], ts=_ts(m.get("timestamp")),
            ))
    return events


def parse_facebook(payload: dict) -> list[EventIn]:
    """Webhook Page: komentar lewat field `feed`, Messenger lewat `messaging`.

    Komentar dan pesan dari Page itu sendiri (balasan kita) diabaikan supaya
    tidak memicu agen membalas dirinya sendiri.
    """
    events: list[EventIn] = []
    for entry in payload.get("entry", []):
        page_id = str(entry.get("id", ""))
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            v = change.get("value", {})
            if v.get("item") != "comment" or v.get("verb") != "add":
                continue
            who = v.get("from") or {}
            if not v.get("comment_id") or not v.get("message") or str(who.get("id", "")) == page_id:
                continue
            events.append(EventIn(
                channel=Channel.FACEBOOK, kind="comment", external_id=v["comment_id"],
                sender=Sender(handle=str(who.get("id", "")), name=who.get("name")),
                text=v["message"], post_ref=v.get("post_id"),
                comment_ref=v["comment_id"], ts=_ts(v.get("created_time") or entry.get("time")),
            ))
        for m in entry.get("messaging", []):
            msg = m.get("message") or {}
            if msg.get("is_echo") or not msg.get("text") or not msg.get("mid"):
                continue
            events.append(EventIn(
                channel=Channel.FACEBOOK, kind="dm", external_id=msg["mid"],
                sender=Sender(handle=str(m.get("sender", {}).get("id", ""))),
                text=msg["text"], ts=_ts(m.get("timestamp")),
            ))
    return events


def _ingest_all(ingest: IngestService, events: list[EventIn]) -> None:
    for ev in events:
        try:
            ingest.ingest(ev)
        except Exception:  # satu event gagal tidak boleh menghentikan sisanya
            log.exception("Gagal memproses event %s/%s", ev.channel, ev.external_id)


async def _signed_json(request: Request, settings: Settings) -> dict:
    raw = await request.body()
    secret = settings.instagram_client_secret if request.url.path.endswith("/instagram") and settings.instagram_client_secret else settings.meta_app_secret
    if not verify_signature(secret, raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Signature tidak valid")
    try:
        return json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Body bukan JSON")


# --- WhatsApp ---


@router.get("/whatsapp")
def whatsapp_verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    return _verify_challenge(settings, mode, token, challenge)


@router.post("/whatsapp")
async def whatsapp_receive(
    request: Request,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    payload = await _signed_json(request, settings)
    if settings.auth_enabled:
        accepted = 0
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                phone = str(change.get("value", {}).get("metadata", {}).get("phone_number_id", ""))
                workspace = get_accounts().asset_workspace("whatsapp", phone)
                if workspace:
                    events = parse_whatsapp({"entry": [{"changes": [change]}]})
                    for event in events:
                        event.meta["business_account_id"] = phone
                    background.add_task(_ingest_all, ingest_for_workspace(workspace), events)
                    accepted += len(events)
        return {"status": "ok", "accepted": accepted}
    events = parse_whatsapp(payload)
    background.add_task(_ingest_all, ingest, events)
    return {"status": "ok", "accepted": len(events)}


# --- Instagram ---


@router.get("/instagram")
def instagram_verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    return _verify_challenge(settings, mode, token, challenge)


@router.post("/instagram")
async def instagram_receive(
    request: Request,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    payload = await _signed_json(request, settings)
    if settings.auth_enabled:
        accepted = 0
        for entry in payload.get("entry", []):
            workspace = get_accounts().asset_workspace("instagram", str(entry.get("id", "")))
            if workspace:
                events = parse_instagram({"entry": [entry]})
                for event in events:
                    event.meta["business_account_id"] = str(entry["id"])
                background.add_task(_ingest_all, ingest_for_workspace(workspace), events)
                accepted += len(events)
        return {"status": "ok", "accepted": accepted}
    events = parse_instagram(payload)
    background.add_task(_ingest_all, ingest, events)
    return {"status": "ok", "accepted": len(events)}


# --- Facebook Page ---


@router.get("/facebook")
def facebook_verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    return _verify_challenge(settings, mode, token, challenge)


@router.post("/facebook")
async def facebook_receive(
    request: Request,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    payload = await _signed_json(request, settings)
    if settings.auth_enabled:
        accepted = 0
        for entry in payload.get("entry", []):
            workspace = get_accounts().asset_workspace("facebook", str(entry.get("id", "")))
            if workspace:
                events = parse_facebook({"entry": [entry]})
                for event in events:
                    event.meta["business_account_id"] = str(entry["id"])
                background.add_task(_ingest_all, ingest_for_workspace(workspace), events)
                accepted += len(events)
        return {"status": "ok", "accepted": accepted}
    events = parse_facebook(payload)
    background.add_task(_ingest_all, ingest, events)
    return {"status": "ok", "accepted": len(events)}


# --- Gmail push (Pub/Sub) ---


def poll_gmail(registry: Registry, ingest: IngestService) -> int:
    gmail = registry.gmail()
    if gmail is None or not gmail.configured:
        return 0
    try:
        events = gmail.poll()
    except ConnectorError:
        log.exception("Polling Gmail gagal")
        return 0
    bindings = getattr(registry, "account_ids", None)
    if bindings is not None:
        for event in events:
            event.meta["business_account_id"] = bindings.get("email", "")
    _ingest_all(ingest, events)
    return len(events)


@router.post("/gmail")
async def gmail_push(
    request: Request,
    background: BackgroundTasks,
    token: str = Query(""),
    settings: Settings = Depends(get_settings),
    registry: Registry = Depends(get_registry),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    """Push Pub/Sub: cukup memicu polling; dedup menjamin aman bila ganda."""
    if not settings.gmail_push_token or not hmac.compare_digest(token, settings.gmail_push_token):
        raise HTTPException(status_code=403, detail="Token push tidak valid")
    try:
        body = await request.json()
        push = json.loads(base64.b64decode((body.get("message") or {}).get("data", "") or "").decode())
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Body push tidak valid")
    if settings.auth_enabled:
        workspace = get_accounts().asset_workspace("gmail", str(push.get("emailAddress", "")).lower())
        if workspace:
            background.add_task(poll_gmail, registry_for_workspace(workspace), ingest_for_workspace(workspace))
    else:
        background.add_task(poll_gmail, registry, ingest)
    return {"status": "ok"}
