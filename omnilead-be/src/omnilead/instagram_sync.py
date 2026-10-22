import hashlib
import logging
import re
import time
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from omnilead.autonomy import browser_grants
from omnilead.connectors.base import ActionNotSupported, ConnectorError
from omnilead.ingest import IngestService, handle_key
from omnilead.instagram_snapshot import (FOLDER_TABS, VIEW_REPLIES, Post, PostComment, age_seconds, button_ref,
                                        comments as parse_comments, conversation as parse_conversation,
                                        folder_ref, own_username, post as parse_post, profile_posts, thread_ref,
                                        threads as parse_threads, conversation_username)
from omnilead.models import Channel, EventIn, Sender
from omnilead.message_freshness import browser_timestamp, browser_reply_hold
from omnilead.openclaw_browser import OpenClawBrowser, OpenClawUnavailable

log = logging.getLogger(__name__)

INBOX_URL = "https://www.instagram.com/direct/inbox/"
POST_URL = "https://www.instagram.com/p/{code}/"
PROFILE_URL = "https://www.instagram.com/{username}/"
REPLY_EXPANDS = 3
NOTIFICATIONS_URL = "https://www.instagram.com/notifications/"
FOLDERS = ("Primary", "General", "Requests")
DIALOGS = ("Not Now", "Not now", "Lain Kali", "Jangan Sekarang", "Nanti Saja")
WEBHOOK_STALE = timedelta(minutes=30)
TEXT_DUPLICATE_WINDOW = timedelta(hours=72)
SETTLE_SECONDS = 2.5
ACCEPT_LABELS = ("accept", "terima")
_sync_locks: dict[str, threading.Lock] = {}
_sync_lock_guard = threading.Lock()


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


def _read_conversation(browser, name: str, limit: int, scrolls: int, folder: str = "Primary", meta=None) -> list[dict]:
    browser.inspect()
    ref = thread_ref(browser.refs, name)
    if not ref and folder != "Primary" and _open_folder(browser, folder):
        browser.inspect()
        ref = thread_ref(browser.refs, name)
    if not ref:
        return []
    browser.act("click", ref=ref)
    time.sleep(SETTLE_SECONDS)
    snapshot = browser.read_text()
    messages = parse_conversation(snapshot, limit)
    if meta is not None:
        username = conversation_username(snapshot)
        if username:
            meta["username"] = username
        meta["conversation_checked_at"] = _now().isoformat()
        url = getattr(browser, "url", "")
        if url.startswith("https://www.instagram.com/direct/t/"):
            meta["thread_url"] = url
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
                 grants=frozenset(), pending: dict | None = None, progress=lambda label: None) -> list[EventIn]:
    events: list[EventIn] = []
    seen: set[str] = set()
    pending = {} if pending is None else pending
    for folder in FOLDERS:
        progress(f"Memeriksa folder {folder}")
        if folder != "Primary" and not _open_folder(browser, folder):
            continue
        for thread in parse_threads(browser.read_text()):
            if not thread.incoming or not thread.preview:
                continue
            sent = browser_timestamp(thread.time)
            if sent and _now() - sent >= timedelta(hours=24):
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
                progress("Membaca percakapan pelanggan")
                history = _read_conversation(browser, thread.name, limit, scrolls, folder, meta)
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


def _save_browser_evidence(store, event, meta):
    """Attach verified profile aliases even when the preview was already imported."""
    username = meta.get("username")
    if username and event.lead_id:
        key = handle_key(Channel.INSTAGRAM, username)
        owners = store.find_leads_by_identity(f"handle:{key}")
        if any(owner.id != event.lead_id for owner in owners):
            return False  # Never silently merge different contacts.
        lead = store.get_lead(event.lead_id)
        if lead and key not in lead.handles:
            lead.handles.append(key)
            lead.updated_at = _now()
            store.save_lead(lead)
    event.meta = {**event.meta, **meta}
    store.save_event(event)
    return True


def lookup_instagram_account(store, ingest, settings, workspace: str, query: str, progress=lambda label: None) -> dict:
    """Bounded inbox lookup; a display name is never guessed to be a username."""
    import re
    wanted = query.strip().lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", wanted):
        return {"ok": False, "reason": "Gunakan username Instagram, misalnya @nama.akun."}
    if not settings.browser_enabled:
        return {"ok": False, "reason": "Browser Instagram belum diaktifkan."}
    with _sync_lock_guard:
        lock = _sync_locks.setdefault(workspace, threading.Lock())
    if not lock.acquire(blocking=False):
        return {"ok": False, "reason": "Pembacaan Instagram lain masih berjalan; tunggu hasilnya."}
    browser = None
    started = time.monotonic()
    checked, pending = 0, 0
    try:
        browser = OpenClawBrowser(settings, workspace, "instagram")
        progress("Mencari username di inbox Instagram")
        browser.open(INBOX_URL)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        if browser.login_required():
            return {"ok": False, "reason": "Sesi Instagram memerlukan login di Integrasi."}
        browser.dismiss(*DIALOGS)
        grants = browser_grants(store.get_settings().autonomy)
        # Search narrows visible rows when Instagram exposes its inbox search box.
        browser.inspect()
        search = next((ref for ref, item in browser.refs.items() if isinstance(item, dict)
                       and item.get("role") in ("textbox", "searchbox")
                       and re.fullmatch(r"search|cari|cari pesan|search messages", str(item.get("name", "")), re.I)), "")
        if search:
            browser.act("type", ref=search, text=wanted, submit=False)
            time.sleep(SETTLE_SECONDS)
        visited = set()
        for folder in FOLDERS:
            if time.monotonic() - started > 100 or checked >= 8:
                break
            if folder != "Primary" and (search or not _open_folder(browser, folder)):
                continue
            candidates = parse_threads(browser.read_text())
            for thread in candidates:
                if thread.name in visited or checked >= 8 or time.monotonic() - started > 100:
                    continue
                visited.add(thread.name)
                need = "accept_request" if folder == "Requests" else "read_unread" if thread.unread else ""
                if need and need not in grants:
                    pending += 1
                    continue
                checked += 1
                progress(f"Memeriksa profil percakapan {checked}/8")
                meta = {"source": "openclaw_text", "folder": folder, "seen_at": thread.time,
                        "unread": thread.unread, "handoff_only": True}
                history = _read_conversation(browser, thread.name, settings.instagram_history_limit, 0, folder, meta)
                if meta.get("username") != wanted:
                    continue
                meta["conversation"] = history
                # Import only the observed inbox preview, without running analysis or sending.
                digest = hashlib.sha256(f"{thread.name}|{thread.preview}".encode()).hexdigest()[:32]
                if thread.incoming and thread.preview:
                    ev, _ = ingest.ingest(EventIn(channel=Channel.INSTAGRAM, kind="dm",
                        external_id=f"openclaw:{digest}", sender=Sender(handle=thread.name, name=thread.name),
                        text=thread.preview, ts=browser_timestamp(thread.time), meta=meta), analyze=False)
                else:
                    leads = store.find_leads_by_identity(f"handle:{handle_key(Channel.INSTAGRAM, thread.name)}")
                    ev = next((e for lead in leads for e in store.list_events(lead_id=lead.id, limit=50)
                               if e.channel == Channel.INSTAGRAM and e.kind == "dm"), None)
                if ev and not _save_browser_evidence(store, ev, meta):
                    return {"ok": False, "reason": "Username cocok dengan beberapa kontak; perlu tinjauan identitas."}
                return {"ok": True, "username": wanted, "nama_tampilan": thread.name,
                        "lead_id": ev.lead_id if ev else None,
                        "sudah_dibalas": bool(history and history[-1]["direction"] == "out"),
                        "checked": checked, "reason": "Username terverifikasi dari profil di percakapan Instagram."}
        return {"ok": False, "checked": checked, "perlu_izin": pending,
                "reason": "Username belum terverifikasi pada percakapan yang dapat dibaca. Ini bukan bukti akun tidak ada."
                          + (" Beberapa percakapan menunggu izin baca di Integrasi." if pending else "")}
    finally:
        try:
            if browser:
                browser.close()
        finally:
            lock.release()


def _addressed_to(text: str) -> str:
    m = re.match(r"@([A-Za-z0-9._]+)", text.strip())
    return m.group(1).lower() if m else ""


def _open_post(browser, code: str) -> Post:
    browser.navigate(POST_URL.format(code=code))
    time.sleep(SETTLE_SECONDS)
    for _ in range(REPLY_EXPANDS):
        browser.inspect()
        ref = next((r for r, item in browser.refs.items() if isinstance(item, dict) and item.get("role") == "button"
                    and VIEW_REPLIES.match(str(item.get("name", "")))), "")
        if not ref:
            break
        browser.act("click", ref=ref)
        time.sleep(1)
    return parse_post(browser.read_text(), code)


def _post_context(page: Post, customer: str, comment_id: str, limit: int) -> dict:
    customer = customer.lower()
    thread = [c for c in page.comments if c.comment_id != comment_id and (
        c.author == customer or (c.direction == "out" and _addressed_to(c.text) in ("", customer)))]
    out = {"post_caption": page.caption,
           "conversation": [{"direction": c.direction, "author": c.author, "text": c.text} for c in thread][-limit:]}
    return {k: v for k, v in out.items() if v}


def _answered(page: Post, comment: PostComment) -> bool:
    later = page.comments[page.comments.index(comment) + 1:]
    return any(c.direction == "out" and _addressed_to(c.text) == comment.author for c in later)


def _comment_event(comment_id: str, author: str, text: str, code: str, age: str, extra: dict) -> EventIn:
    return EventIn(
        channel=Channel.INSTAGRAM, kind="comment", external_id=comment_id, sender=Sender(handle=author), text=text,
        post_ref=code, comment_ref=comment_id,
        meta={"source": "openclaw_text", "post_code": code, "seen_at": age, **extra},
    )


def _browser_comments(browser, known=lambda comment_id: False, limit: int = 10, recent_posts: int = 0,
                      days: int = 7) -> list[EventIn]:
    browser.navigate(NOTIFICATIONS_URL)
    time.sleep(SETTLE_SECONDS)
    browser.dismiss(*DIALOGS)
    snapshot = browser.read_text()
    pages: dict[str, Post] = {}

    def page(code: str) -> Post:
        if code not in pages:
            pages[code] = _open_post(browser, code)
        return pages[code]

    events: list[EventIn] = []
    for c in parse_comments(snapshot):
        extra = {}
        if not known(c.comment_id):
            try:
                extra = _post_context(page(c.post_code), c.username, c.comment_id, limit)
            except OpenClawUnavailable as exc:
                log.warning("instagram post read failed for %s: %s", c.post_code, exc)
        events.append(_comment_event(c.comment_id, c.username, c.text, c.post_code, c.time, extra))

    me = own_username(snapshot)
    if not me or recent_posts <= 0:
        return events
    seen = {e.comment_ref for e in events}
    try:
        browser.navigate(PROFILE_URL.format(username=me))
        time.sleep(SETTLE_SECONDS)
        codes = profile_posts(browser.read_text(), me, recent_posts)
    except OpenClawUnavailable as exc:
        log.warning("instagram profile read failed: %s", exc)
        return events
    for code in codes:
        try:
            current = page(code)
        except OpenClawUnavailable as exc:
            log.warning("instagram post read failed for %s: %s", code, exc)
            continue
        for comment in current.comments:
            age = age_seconds(comment.age)
            if (comment.direction != "in" or comment.comment_id in seen or age is None or age > days * 86400
                    or known(comment.comment_id) or _answered(current, comment)):
                continue
            seen.add(comment.comment_id)
            extra = {**_post_context(current, comment.author, comment.comment_id, limit), "found_in": "recent_post"}
            events.append(_comment_event(comment.comment_id, comment.author, comment.text, code, comment.age, extra))
    return events


def _from_browser(settings, workspace: str, known, grants=frozenset(),
                  pending: dict | None = None, known_comment=lambda comment_id: False,
                  progress=lambda label: None) -> tuple[list[EventIn], str]:
    browser = OpenClawBrowser(settings, workspace, "instagram")
    try:
        progress("Membuka sesi browser Instagram")
        browser.open(INBOX_URL)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        if browser.login_required():
            progress("Sesi Instagram membutuhkan login")
            return [], "needs_login"
        progress("Membaca daftar percakapan Instagram")
        browser.dismiss(*DIALOGS)
        time.sleep(1)
        dms = _browser_dms(browser, known, settings.instagram_history_limit, settings.instagram_history_scrolls,
                           grants, pending, progress)
        progress("Membaca notifikasi dan komentar Instagram")
        comments = _browser_comments(browser, known_comment, settings.instagram_history_limit,
                                     settings.instagram_recent_posts, settings.instagram_comment_days)
        return dms + comments, "ok"
    finally:
        browser.close()


def _try_browser(settings, workspace: str, report: dict, errors: list[str], known,
                 grants=frozenset(), known_comment=lambda comment_id: False, progress=lambda label: None) -> list[EventIn]:
    if not settings.browser_enabled:
        errors.append("OpenClaw belum diaktifkan (OMNILEAD_BROWSER_ENABLED).")
        return []
    try:
        events, state = _from_browser(settings, workspace, known, grants, report["pending"], known_comment, progress)
        report["source"] = "openclaw_text"
        report["needs_login"] = state == "needs_login"
        if report["needs_login"]:
            errors[:] = ["Sesi Instagram di browser agen belum masuk. Masuk dulu di jendela Chrome lalu baca ulang."]
        else:
            errors.clear()
        return events
    except OpenClawUnavailable as exc:
        log.warning("instagram browser sync failed: %s", exc)
        errors.append("Gateway OpenClaw: " + (str(exc) or "Browser agen belum bisa membaca Instagram."))
        return []


def sync_instagram(store, registry, ingest: IngestService, settings, workspace: str, *,
                   use_browser: bool = True, prefer_browser: bool = False, allow=(), progress=None) -> dict:
    with _sync_lock_guard:
        lock = _sync_locks.setdefault(workspace, threading.Lock())
    if not lock.acquire(blocking=False):
        return {**sync_status(store), "error": "Pembacaan Instagram lain masih berjalan. Tunggu hasilnya sebelum mencoba lagi.", "busy": True}
    started = time.monotonic()

    def notify(label):
        if time.monotonic() - started > 120:
            raise OpenClawUnavailable("Pembacaan browser melewati batas waktu. Periksa sesi Instagram lalu coba lagi.")
        if progress:
            progress(label)

    try:
        return _sync_instagram(store, registry, ingest, settings, workspace, use_browser=use_browser,
                               prefer_browser=prefer_browser, allow=allow, progress=notify)
    finally:
        lock.release()


def _sync_instagram(store, registry, ingest: IngestService, settings, workspace: str, *,
                    use_browser: bool = True, prefer_browser: bool = False, allow=(), progress=lambda label: None) -> dict:
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

    def known_comment(comment_id: str) -> bool:
        return any(store.find_event(Channel.INSTAGRAM.value, ref) for ref in (comment_id, f"{account}:{comment_id}"))

    if prefer_browser and use_browser:
        events = _try_browser(settings, workspace, report, errors, known, grants, known_comment, progress)
        used_browser = report["source"] == "openclaw_text" or report["needs_login"]

    if not used_browser:
        if hasattr(connector, "recent_messages"):
            for reader in (_api_messages, _api_comments):
                try:
                    progress("Membaca pesan melalui koneksi Meta API")
                    events += reader(connector, account)
                    report["source"] = "meta_api"
                except (ConnectorError, ActionNotSupported) as exc:
                    errors.append(str(exc))
        else:
            errors.append("Instagram belum terhubung lewat Meta API untuk bisnis ini.")

        if report["source"] == "none" or not events:
            report["api_error"] = " ".join(dict.fromkeys(errors))
            if use_browser and not prefer_browser:
                events = _try_browser(settings, workspace, report, errors, known, grants, known_comment, progress)
        elif errors:
            errors = [f"Sebagian data Meta API gagal dibaca: {errors[0]}"]

    report["error"] = " ".join(dict.fromkeys(errors))
    progress("Menyimpan pesan baru dan memeriksa duplikasi")
    report["fetched"] = len(events)
    for ev in events:
        if ev.external_id.startswith("openclaw:") and _seen_recently(store, ev.sender.handle, ev.text):
            report["duplicates"] += 1
            continue
        saved, duplicate = ingest.ingest(ev, analyze=False)
        if ev.meta.get("username"):
            _save_browser_evidence(store, saved, ev.meta)
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
    eligible = []
    for event in pending:
        if reason := browser_reply_hold(event):
            event.status, event.review_reason = "review", reason
            store.save_event(event)
            continue
        event.trace = {"queued": True, "queued_at": queued_at, "status": "Menunggu giliran"}
        store.save_event(event)
        eligible.append(event.id)
    return eligible


def run_analysis_queue(store, ingest: IngestService, ids: list[str], *, draft_only: bool = False,
                       progress=None) -> None:
    for index, event_id in enumerate(ids):
        event = store.get_event(event_id)
        if not event or event.status != "new" or not (event.trace or {}).get("queued"):
            continue
        try:
            if progress:
                progress(f"Menganalisis pesan {index + 1}/{len(ids)} dan menjalankan aksi sesuai izin agen")
            event = ingest.prepare(event)
            ingest.process(event, expected_run_id=event.trace["run_id"], draft_only=draft_only)
        except Exception as exc:
            log.warning("instagram analysis failed for %s: %s", event_id, exc)
