import hashlib
import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from omnilead.autonomy import browser_grants
from omnilead.connectors.base import ActionNotSupported, ConnectorError
from omnilead.ingest import IngestService, handle_key
from omnilead.instagram_snapshot import (FOLDER_TABS, button_ref, comments as parse_comments,
                                        conversation as parse_conversation, folder_ref, thread_ref,
                                        threads as parse_threads)
from omnilead.models import Channel, EventIn, Sender
from omnilead.openclaw_browser import OpenClawBrowser, OpenClawUnavailable

log = logging.getLogger(__name__)

INBOX_URL = "https://www.instagram.com/direct/inbox/"
NOTIFICATIONS_URL = "https://www.instagram.com/notifications/"
FOLDERS = ("Primary", "General", "Requests")
DIALOGS = ("Not Now", "Not now", "Lain Kali", "Jangan Sekarang", "Nanti Saja")
WEBHOOK_STALE = timedelta(minutes=30)
TEXT_DUPLICATE_WINDOW = timedelta(hours=72)
SETTLE_SECONDS = 2.5
ACCEPT_LABELS = ("accept", "terima")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def sync_status(store) -> dict:
    status = dict(store.get_settings().instagram_sync)
    last = status.get("webhook_last_at")
    status["webhook_stale"] = not last or _now() - datetime.fromisoformat(last) > WEBHOOK_STALE
    return status


def _save(store, **changes) -> dict:
    settings = store.get_settings()
    settings.instagram_sync = {**settings.instagram_sync, **changes}
    store.save_settings(settings)
    return settings.instagram_sync


def record_webhook(store, events: int) -> None:
    changes = {"webhook_last_at": _now().isoformat()}
    if events:
        changes["webhook_last_event_at"] = changes["webhook_last_at"]
    _save(store, **changes)


def _api_messages(connector, account_id: str) -> list[EventIn]:
    out = []
    for msg in connector.recent_messages():
        meta = {"source": "meta_api_sync", "platform_user_id": msg["sender_id"], "thread_id": msg["thread_id"]}
        if msg.get("username"):
            meta["username"] = msg["username"]
        if account_id:
            meta["business_account_id"] = account_id
        out.append(EventIn(channel=Channel.INSTAGRAM, kind="dm", external_id=msg["mid"],
                           sender=Sender(handle=msg["sender_id"]), text=msg["text"], ts=msg["ts"], meta=meta))
    return out


def _api_comments(connector, account_id: str) -> list[EventIn]:
    out = []
    for c in connector.recent_comments():
        meta = {"source": "meta_api_sync"}
        if account_id:
            meta["business_account_id"] = account_id
        out.append(EventIn(channel=Channel.INSTAGRAM, kind="comment", external_id=c.id,
                           sender=Sender(handle=c.author_handle, name=c.author_name), text=c.text, ts=c.created_at,
                           post_ref=c.post_ref, comment_ref=c.id, meta=meta))
    return out


def _seen_recently(store, handle: str, text: str) -> bool:
    key = handle_key(Channel.INSTAGRAM, handle)
    if not key:
        return False
    cutoff = _now() - TEXT_DUPLICATE_WINDOW
    for lead in store.find_leads_by_identity(f"handle:{key}"):
        for event in store.list_events(lead_id=lead.id, limit=50):
            if event.text.strip() == text.strip() and (_aware(event.ts) or _now()) >= cutoff:
                return True
    return False


def _top_message_ref(refs: dict) -> str:
    return next((ref for ref, item in refs.items() if isinstance(item, dict) and item.get("role") == "article"), "")


def _open_folder(browser, folder: str) -> bool:
    browser.inspect()
    ref = folder_ref(browser.refs, folder)
    if not ref:
        return False
    browser.act("click", ref=ref)
    time.sleep(SETTLE_SECONDS)
    return True


def _accept_request(browser) -> bool:
    browser.inspect()
    ref = button_ref(browser.refs, *ACCEPT_LABELS)
    if not ref:
        return False
    browser.act("click", ref=ref)
    time.sleep(SETTLE_SECONDS)
    browser.inspect()
    primary = button_ref(browser.refs, *FOLDER_TABS["Primary"])
    if primary:
        browser.act("click", ref=primary)
        time.sleep(SETTLE_SECONDS)
    return True


def _read_conversation(browser, name: str, limit: int, scrolls: int, folder: str = "Primary") -> list[dict]:
    browser.inspect()
    ref = thread_ref(browser.refs, name)
    if not ref and folder != "Primary" and _open_folder(browser, folder):
        browser.inspect()
        ref = thread_ref(browser.refs, name)
    if not ref:
        return []
    browser.act("click", ref=ref)
    time.sleep(SETTLE_SECONDS)
    messages = parse_conversation(browser.read_text(), limit)
    for _ in range(scrolls):
        if len(messages) >= limit:
            break
        browser.inspect()
        top = _top_message_ref(browser.refs)
        if not top:
            break
        browser.act("scrollIntoView", ref=top)
        time.sleep(SETTLE_SECONDS)
        older = parse_conversation(browser.read_text(), limit)
        if len(older) <= len(messages):
            break
        messages = older
    return [asdict(m) for m in messages]


def _browser_dms(browser, known=lambda handle, text: False, limit: int = 10, scrolls: int = 2,
                 grants=frozenset(), pending: dict | None = None) -> list[EventIn]:
    events: list[EventIn] = []
    seen: set[str] = set()
    pending = {} if pending is None else pending
    for folder in FOLDERS:
        if folder != "Primary" and not _open_folder(browser, folder):
            continue
        for thread in parse_threads(browser.read_text()):
            if not thread.incoming or not thread.preview:
                continue
            digest = hashlib.sha256(f"{thread.name}|{thread.preview}".encode()).hexdigest()[:32]
            if digest in seen:
                continue
            seen.add(digest)
            meta = {"source": "openclaw_text", "folder": folder, "unread": thread.unread,
                    "seen_at": thread.time, "handoff_only": True}
            if known(thread.name, thread.preview):
                events.append(EventIn(
                    channel=Channel.INSTAGRAM, kind="dm", external_id=f"openclaw:{digest}",
                    sender=Sender(handle=thread.name, name=thread.name), text=thread.preview, meta=meta,
                ))
                continue
            need = "accept_request" if folder == "Requests" else "read_unread" if thread.unread else ""
            if need and need not in grants:
                pending.setdefault(need, []).append({"name": thread.name, "preview": thread.preview[:200],
                                                     "folder": folder})
                continue
            try:
                history = _read_conversation(browser, thread.name, limit, scrolls, folder)
                if need == "accept_request":
                    meta["accepted"] = _accept_request(browser)
            except OpenClawUnavailable as exc:
                log.warning("instagram thread read failed for %s: %s", thread.name, exc)
                history = []
            if history:
                meta["conversation"] = history
            events.append(EventIn(
                channel=Channel.INSTAGRAM, kind="dm", external_id=f"openclaw:{digest}",
                sender=Sender(handle=thread.name, name=thread.name), text=thread.preview, meta=meta,
            ))
    return events


def _browser_comments(browser) -> list[EventIn]:
    browser.navigate(NOTIFICATIONS_URL)
    time.sleep(SETTLE_SECONDS)
    browser.dismiss(*DIALOGS)
    return [EventIn(
        channel=Channel.INSTAGRAM, kind="comment", external_id=c.comment_id,
        sender=Sender(handle=c.username), text=c.text, post_ref=c.post_code, comment_ref=c.comment_id,
        meta={"source": "openclaw_text", "post_code": c.post_code, "seen_at": c.time},
    ) for c in parse_comments(browser.read_text())]


def _from_browser(settings, workspace: str, known, grants=frozenset(),
                  pending: dict | None = None) -> tuple[list[EventIn], str]:
    browser = OpenClawBrowser(settings, workspace, "instagram")
    try:
        browser.open(INBOX_URL)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        if browser.login_required():
            return [], "needs_login"
        browser.dismiss(*DIALOGS)
        time.sleep(1)
        dms = _browser_dms(browser, known, settings.instagram_history_limit, settings.instagram_history_scrolls,
                           grants, pending)
        return dms + _browser_comments(browser), "ok"
    finally:
        browser.close()


def _try_browser(settings, workspace: str, report: dict, errors: list[str], known,
                 grants=frozenset()) -> list[EventIn]:
    if not settings.browser_enabled:
        errors.append("OpenClaw belum diaktifkan (OMNILEAD_BROWSER_ENABLED).")
        return []
    try:
        events, state = _from_browser(settings, workspace, known, grants, report["pending"])
        report["source"] = "openclaw_text"
        report["needs_login"] = state == "needs_login"
        if report["needs_login"]:
            errors[:] = ["Sesi Instagram di browser agen belum masuk. Masuk dulu di jendela Chrome lalu baca ulang."]
        else:
            errors.clear()
        return events
    except OpenClawUnavailable as exc:
        log.warning("instagram browser sync failed: %s", exc)
        errors.append(str(exc) or "Browser agen belum bisa membaca Instagram. Jalankan tools/openclaw/start.sh.")
        return []


def sync_instagram(store, registry, ingest: IngestService, settings, workspace: str, *,
                   use_browser: bool = True, prefer_browser: bool = False, allow=()) -> dict:
    started = _now()
    report = {"last_run_at": started.isoformat(), "source": "none", "fetched": 0, "imported": 0, "duplicates": 0,
              "dms": 0, "comments": 0, "webhook_gap": 0, "error": "", "api_error": "", "needs_login": False,
              "pending": {}}
    connector = registry.get(Channel.INSTAGRAM)
    account = (getattr(registry, "account_ids", None) or {}).get("instagram", "")
    events: list[EventIn] = []
    errors: list[str] = []
    used_browser = False
    grants = browser_grants(store.get_settings().autonomy, allow)

    def known(handle: str, text: str) -> bool:
        return _seen_recently(store, handle, text)

    if prefer_browser and use_browser:
        events = _try_browser(settings, workspace, report, errors, known, grants)
        used_browser = report["source"] == "openclaw_text" or report["needs_login"]

    if not used_browser:
        if hasattr(connector, "recent_messages"):
            for reader in (_api_messages, _api_comments):
                try:
                    events += reader(connector, account)
                    report["source"] = "meta_api"
                except (ConnectorError, ActionNotSupported) as exc:
                    errors.append(str(exc))
        else:
            errors.append("Instagram belum terhubung lewat Meta API untuk bisnis ini.")

        if report["source"] == "none" or not events:
            report["api_error"] = " ".join(dict.fromkeys(errors))
            if use_browser:
                events = _try_browser(settings, workspace, report, errors, known, grants)
        elif errors:
            errors = [f"Sebagian data Meta API gagal dibaca: {errors[0]}"]

    report["error"] = " ".join(dict.fromkeys(errors))
    report["fetched"] = len(events)
    for ev in events:
        if ev.external_id.startswith("openclaw:") and _seen_recently(store, ev.sender.handle, ev.text):
            report["duplicates"] += 1
            continue
        _, duplicate = ingest.ingest(ev, analyze=False)
        if duplicate:
            report["duplicates"] += 1
            continue
        report["imported"] += 1
        report["dms" if ev.kind == "dm" else "comments"] += 1
        if report["source"] == "meta_api":
            report["webhook_gap"] += 1

    if report["webhook_gap"]:
        store.audit("instagram_webhook_gap",
                    f"{report['webhook_gap']} pesan Instagram tidak masuk lewat webhook dan dipulihkan lewat Meta API",
                    actor="system", channel="instagram")
    store.audit("instagram_sync",
                f"Instagram: {report['fetched']} dibaca, {report['dms']} DM baru, "
                f"{report['comments']} komentar baru, {report['duplicates']} sudah ada"
                + (f". {report['error']}" if report["error"] else ""),
                actor="system", channel="instagram")
    _save(store, **report)
    return sync_status(store)



def queue_analysis(store) -> list[str]:
    pending = [e for e in store.list_events(limit=500)
               if e.channel == Channel.INSTAGRAM and e.status == "new" and not (e.trace or {}).get("goal")]
    pending.sort(key=lambda e: _aware(e.ts) or _now())
    queued_at = _now().isoformat()
    for event in pending:
        event.trace = {"queued": True, "queued_at": queued_at, "status": "Menunggu giliran"}
        store.save_event(event)
    return [e.id for e in pending]


def run_analysis_queue(store, ingest: IngestService, ids: list[str]) -> None:
    for event_id in ids:
        event = store.get_event(event_id)
        if not event or event.status != "new" or not (event.trace or {}).get("queued"):
            continue
        try:
            event = ingest.prepare(event)
            ingest.process(event, expected_run_id=event.trace["run_id"])
        except Exception as exc:
            log.warning("instagram analysis failed for %s: %s", event_id, exc)
