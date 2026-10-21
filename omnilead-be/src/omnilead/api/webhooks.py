"""Webhook kanal masuk: WhatsApp, Instagram, dan push Gmail.

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

from omnilead.api.deps import get_ingest, get_registry
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


def _ingest_all(ingest: IngestService, events: list[EventIn]) -> None:
    for ev in events:
        try:
            ingest.ingest(ev)
        except Exception:  # satu event gagal tidak boleh menghentikan sisanya
            log.exception("Gagal memproses event %s/%s", ev.channel, ev.external_id)


async def _signed_json(request: Request, settings: Settings) -> dict:
    raw = await request.body()
    if not verify_signature(settings.meta_app_secret, raw, request.headers.get("x-hub-signature-256")):
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
    events = parse_whatsapp(await _signed_json(request, settings))
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
    events = parse_instagram(await _signed_json(request, settings))
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
        base64.b64decode((body.get("message") or {}).get("data", "") or "")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Body push tidak valid")
    background.add_task(poll_gmail, registry, ingest)
    return {"status": "ok"}
