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
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from omnilead.api.deps import get_ingest, get_registry, get_store, get_accounts, ingest_for_workspace, registry_for_workspace, store_for_workspace
from omnilead.config import Settings, get_settings
from omnilead.connectors.base import ConnectorError
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.models import ActionStatus, Channel, EventIn, Sender

log = logging.getLogger("uvicorn.error.omnilead.webhooks")
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
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


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


DELIVERY_RANK = {"sent": 1, "delivered": 2, "read": 3}


def parse_whatsapp_statuses(payload: dict) -> list[dict]:
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for st in change.get("value", {}).get("statuses", []) or []:
                if st.get("id") and st.get("status") in ("sent", "delivered", "read", "failed"):
                    errors = st.get("errors") or []
                    out.append({
                        "ref": st["id"],
                        "status": st["status"],
                        "ts": _ts(st.get("timestamp")),
                        "error": (errors[0].get("title") or errors[0].get("message")) if errors else "",
                    })
    return out


def apply_delivery_statuses(store, statuses: list[dict]) -> int:
    if not statuses:
        return 0
    by_ref = {s["ref"]: s for s in statuses}
    updated = 0
    for action in store.list_actions(ActionStatus.EXECUTED):
        st = by_ref.get(action.result_ref or "")
        if st is None or action.channel != Channel.WHATSAPP:
            continue
        if st["status"] == "failed":
            action.delivery_status = "failed"
            action.error = st["error"] or "WhatsApp gagal mengantarkan pesan"
        elif DELIVERY_RANK[st["status"]] > DELIVERY_RANK.get(action.delivery_status or "", 0):
            action.delivery_status = st["status"]
        else:
            continue
        action.delivery_at = st["ts"]
        store.save_action(action)
        store.audit("delivery_" + st["status"], action.error if st["status"] == "failed" else st["status"],
                    action.id, actor="system", channel=action.channel.value, lead_id=action.lead_id)
        updated += 1
    return updated


def _ig_records(value) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def parse_instagram(payload: dict) -> list[EventIn]:
    events: list[EventIn] = []
    for entry in _ig_records(payload.get("entry")):
        account = str(entry.get("id", ""))
        messages = _ig_records(entry.get("messaging"))
        for change in _ig_records(entry.get("changes")):
            field = change.get("field")
            v = change.get("value") or {}
            if not isinstance(v, dict):
                continue
            if field == "messages":
                messages.append(v)
                continue
            if field not in {"comments", "live_comments"}:
                continue
            who = v.get("from") or {}
            who = who if isinstance(who, dict) else {}
            media = v.get("media") or {}
            media = media if isinstance(media, dict) else {}
            if (not v.get("id") or not isinstance(v.get("text"), str) or not v["text"].strip()
                    or (account and str(who.get("id", "")) == account)):
                continue
            events.append(EventIn(
                channel=Channel.INSTAGRAM, kind="comment", external_id=str(v["id"]),
                sender=Sender(handle=str(who.get("username") or who.get("id", ""))),
                text=v["text"], post_ref=str(media["id"]) if media.get("id") else None,
                comment_ref=str(v["id"]), ts=_ts(v.get("timestamp") or entry.get("time")),
                meta={"webhook_field": field},
            ))
        seen = set()
        for m in messages:
            if not isinstance(m, dict):
                continue
            msg = m.get("message") or {}
            who = m.get("sender") or {}
            to = m.get("recipient") or {}
            sender = str(who.get("id", "")) if isinstance(who, dict) else ""
            recipient = str(to.get("id", "")) if isinstance(to, dict) else ""
            ts = _ts(m.get("timestamp"))
            if (not isinstance(msg, dict) or msg.get("is_echo") or msg.get("is_deleted")
                    or msg.get("is_edit") or not isinstance(msg.get("text"), str)
                    or not msg["text"].strip() or not msg.get("mid") or not sender or ts is None
                    or (account and sender == account) or (account and recipient and recipient != account)
                    or str(msg["mid"]) in seen):
                continue
            seen.add(str(msg["mid"]))
            events.append(EventIn(
                channel=Channel.INSTAGRAM, kind="dm", external_id=str(msg["mid"]),
                sender=Sender(handle=sender), text=msg["text"], ts=ts,
                meta={"webhook_field": "messages"},
            ))
    return events


def instagram_notification_fields(entry: dict) -> list[str]:
    """Classify notification types without storing message bodies or model input."""
    fields = {str(c.get("field", "unknown"))[:64] for c in _ig_records(entry.get("changes"))}
    names = {"message": "messages", "message_edit": "message_edit", "reaction": "message_reactions",
             "read": "messaging_seen", "postback": "messaging_postbacks", "referral": "messaging_referral",
             "optin": "messaging_optins", "pass_thread_control": "messaging_handover",
             "take_thread_control": "messaging_handover", "request_thread_control": "messaging_handover"}
    for item in _ig_records(entry.get("messaging")):
        if isinstance(item, dict):
            fields.update(name for key, name in names.items() if key in item)
    if entry.get("standby"):
        fields.add("standby")
    return sorted(fields)


def _audit_instagram_notification(workspace: str, fields: list[str]) -> None:
    try:
        store_for_workspace(workspace).audit("instagram_notification",
            "Notifikasi tanpa pesan teks baru: " + ", ".join(fields), actor="webhook", channel="instagram")
    except Exception:
        log.warning("Tidak dapat menyimpan ringkasan notifikasi Instagram")


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


def enrich_sender(registry: Registry | None, ev: EventIn) -> EventIn:
    if (registry is None or ev.kind != "dm" or ev.channel not in (Channel.INSTAGRAM, Channel.FACEBOOK)
            or ev.sender.name or not ev.sender.handle.isdigit()):
        return ev
    try:
        profile = registry.get(ev.channel).user_profile(ev.sender.handle) or {}
    except Exception:
        log.warning("Profil pengirim %s tidak bisa diambil", ev.channel.value)
        return ev
    meta = {**ev.meta, "platform_user_id": ev.sender.handle}
    if profile.get("username"):
        meta["username"] = profile["username"]
    sender = ev.sender.model_copy(update={"name": profile.get("name") or ev.sender.name})
    return ev.model_copy(update={"sender": sender, "meta": meta})


def _job_id(ev: EventIn) -> str:
    return f"{ev.channel.value}:{ev.external_id}"


def _process_jobs(ingest: IngestService, job_ids: list[str], registry: Registry | None = None) -> None:
    store = ingest.store
    for job_id in job_ids:
        job = store.get_job(job_id)
        if job is None or job["status"] == "done":
            continue
        store.update_job(job_id, "processing", attempt=True)
        try:
            ev = enrich_sender(registry, EventIn.model_validate(job["payload"]["event"]))
            ingest.ingest(ev)
            store.update_job(job_id, "done")
        except Exception as exc:
            log.exception("Gagal memproses event %s", job_id)
            store.update_job(job_id, "failed", str(exc))


def _ingest_all(ingest: IngestService, events: list[EventIn], registry: Registry | None = None) -> None:
    _process_jobs(ingest, _enqueue(ingest, events), registry)


def _enqueue(ingest: IngestService, events: list[EventIn]) -> list[str]:
    for ev in events:
        ingest.store.enqueue_job(_job_id(ev), {"event": ev.model_dump(mode="json")})
    return [_job_id(ev) for ev in events]


def drain_inbox(ingest: IngestService, registry: Registry | None = None, max_attempts: int = 5) -> int:
    store = ingest.store
    jobs = store.list_jobs(("pending",), older_than=timedelta(minutes=2))
    jobs += store.list_jobs(("processing", "failed"), older_than=timedelta(minutes=5))
    ids = [j["id"] for j in jobs if j["attempts"] < max_attempts]
    _process_jobs(ingest, ids, registry)
    return len(ids)


async def _signed_json(request: Request, settings: Settings) -> dict:
    raw = await request.body()
    secret = settings.instagram_client_secret if request.url.path.endswith("/instagram") and settings.instagram_client_secret else settings.meta_app_secret
    if not verify_signature(secret, raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Signature tidak valid")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Webhook membutuhkan objek JSON")
        return payload
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
    store=Depends(get_store),
) -> dict:
    payload = await _signed_json(request, settings)
    if settings.auth_enabled:
        accepted = 0
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                phone = str(change.get("value", {}).get("metadata", {}).get("phone_number_id", ""))
                workspace = get_accounts().asset_workspace("whatsapp", phone)
                if workspace:
                    apply_delivery_statuses(store_for_workspace(workspace),
                                            parse_whatsapp_statuses({"entry": [{"changes": [change]}]}))
                    events = parse_whatsapp({"entry": [{"changes": [change]}]})
                    for event in events:
                        event.meta["business_account_id"] = phone
                    target = ingest_for_workspace(workspace)
                    background.add_task(_process_jobs, target, _enqueue(target, events))
                    accepted += len(events)
        return {"status": "ok", "accepted": accepted}
    apply_delivery_statuses(store, parse_whatsapp_statuses(payload))
    events = parse_whatsapp(payload)
    background.add_task(_process_jobs, ingest, _enqueue(ingest, events))
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
    registry: Registry = Depends(get_registry),
) -> dict:
    payload = await _signed_json(request, settings)
    if payload.get("object", "instagram") != "instagram":
        raise HTTPException(status_code=400, detail="Webhook bukan untuk objek Instagram")
    if settings.auth_enabled:
        accepted = 0
        unmapped = 0
        without_messages = 0
        fields = set()
        for entry in _ig_records(payload.get("entry")):
            entry_fields = instagram_notification_fields(entry)
            fields.update(entry_fields)
            workspace = get_accounts().asset_workspace("instagram", str(entry.get("id", "")))
            if workspace:
                events = parse_instagram({"entry": [entry]})
                for event in events:
                    event.meta["business_account_id"] = str(entry["id"])
                if events:
                    target = ingest_for_workspace(workspace)
                    background.add_task(_process_jobs, target, _enqueue(target, events),
                                        registry_for_workspace(workspace))
                else:
                    without_messages += 1
                    background.add_task(_audit_instagram_notification, workspace, entry_fields)
                accepted += len(events)
            else:
                unmapped += 1
        log.info("Instagram webhook: accepted=%s unmapped_entries=%s entries_without_new_text=%s fields=%s",
                 accepted, unmapped, without_messages, ",".join(sorted(fields)))
        return {"status": "ok", "accepted": accepted, "unmapped_entries": unmapped,
                "entries_without_new_text": without_messages, "fields": sorted(fields)}
    events = parse_instagram(payload)
    background.add_task(_process_jobs, ingest, _enqueue(ingest, events), registry)
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
    registry: Registry = Depends(get_registry),
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
                target = ingest_for_workspace(workspace)
                background.add_task(_process_jobs, target, _enqueue(target, events),
                                    registry_for_workspace(workspace))
                accepted += len(events)
        return {"status": "ok", "accepted": accepted}
    events = parse_facebook(payload)
    background.add_task(_process_jobs, ingest, _enqueue(ingest, events), registry)
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
