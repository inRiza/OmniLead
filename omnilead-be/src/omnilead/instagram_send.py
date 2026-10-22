import hashlib
import re
import time

from omnilead.instagram_snapshot import comment_box_ref, folder_ref, reply_ref, thread_ref, post as parse_post
from omnilead.instagram_sync import DIALOGS, FOLDERS, INBOX_URL, SETTLE_SECONDS, _open_post
from omnilead.models import ActionKind
from omnilead.openclaw_browser import BrowserSendFailed, OpenClawBrowser

COMPOSER = {"message", "message...", "pesan", "pesan...", "kirim pesan...", "write a message..."}
SEARCH = {"search", "cari"}
VERIFY_ATTEMPTS = 3


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def composer_ref(refs: dict) -> str:
    for ref, item in refs.items():
        if isinstance(item, dict) and item.get("role") == "textbox" and _norm(str(item.get("name", ""))) in COMPOSER:
            return ref
    return ""


def _open_thread(browser, name: str) -> bool:
    for folder in FOLDERS:
        browser.inspect()
        if folder != "Primary":
            tab = folder_ref(browser.refs, folder)
            if not tab:
                continue
            browser.act("click", ref=tab)
            time.sleep(SETTLE_SECONDS)
            browser.inspect()
        ref = thread_ref(browser.refs, name)
        if ref:
            browser.act("click", ref=ref)
            time.sleep(SETTLE_SECONDS)
            return True
    return False


def _start(settings, workspace: str):
    browser = OpenClawBrowser(settings, workspace, "instagram")
    try:
        browser.open(INBOX_URL)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        if browser.login_required():
            raise BrowserSendFailed("Sesi Instagram di browser agen belum masuk. Masuk dulu lalu kirim ulang.")
        browser.dismiss(*DIALOGS)
        time.sleep(1)
    except BaseException:
        browser.close()
        raise
    return browser


def _verify(browser, text: str, key: str, *, post_code: str = "") -> str:
    probe = _norm(text.splitlines()[0])[:40]
    for _ in range(VERIFY_ATTEMPTS):
        time.sleep(SETTLE_SECONDS)
        snapshot = browser.read_text()
        if post_code:
            # The editor can still contain the draft after Enter. Only a posted
            # comment from the business is proof of delivery.
            posted = next((c for c in parse_post(snapshot, post_code).comments
                           if c.direction == "out" and _norm(c.text) == _norm(text)), None)
            if posted:
                return "openclaw:comment:" + posted.comment_id
        elif probe in _norm(snapshot):
            return "openclaw:" + hashlib.sha256(f"{key}|{text}|{time.time()}".encode()).hexdigest()[:24]
    raise BrowserSendFailed("Pesan sudah diketik tetapi belum terlihat terkirim di Instagram.")


def _submit(browser, box: str, text: str, key: str) -> str:
    browser.act("type", ref=box, text=text, submit=True)
    return _verify(browser, text, key)


def box_value(snapshot: str, ref: str) -> str:
    for line in snapshot.splitlines():
        if f"[ref={ref}]" in line:
            m = re.search(r'value="((?:[^"\\]|\\.)*)"', line)
            return m.group(1).replace('\\"', '"') if m else ""
    return ""


def _composer(browser) -> str:
    browser.inspect()
    box = composer_ref(browser.refs)
    if not box:
        raise BrowserSendFailed("Kolom pesan Instagram tidak ditemukan.")
    return box


def send_dm(settings, workspace: str, name: str, text: str) -> str:
    if not name.strip() or not text.strip():
        raise BrowserSendFailed("Penerima atau isi pesan kosong.")
    browser = _start(settings, workspace)
    try:
        if not _open_thread(browser, name):
            raise BrowserSendFailed(f"Percakapan dengan {name} tidak ditemukan di kotak masuk Instagram.")
        return _submit(browser, _composer(browser), text, name)
    finally:
        browser.close()


def user_ref(refs: dict, username: str) -> str:
    wanted = username.lower().lstrip("@")
    for ref, item in refs.items():
        if isinstance(item, dict) and item.get("role") == "button" and wanted in _norm(str(item.get("name", ""))).split():
            return ref
    return ""


def message_user(settings, workspace: str, username: str, text: str) -> str:
    username = username.strip().lstrip("@")
    if not username or not text.strip():
        raise BrowserSendFailed("Penerima atau isi pesan kosong.")
    browser = _start(settings, workspace)
    try:
        browser.inspect()
        search = next((ref for ref, item in browser.refs.items() if isinstance(item, dict)
                       and item.get("role") == "textbox" and _norm(str(item.get("name", ""))) in SEARCH), "")
        if not search:
            raise BrowserSendFailed("Kolom pencarian pesan Instagram tidak ditemukan.")
        browser.act("type", ref=search, text=username, submit=False)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        hit = user_ref(browser.refs, username)
        if not hit:
            raise BrowserSendFailed(f"Akun @{username} tidak ditemukan di pencarian pesan Instagram.")
        browser.act("click", ref=hit)
        time.sleep(SETTLE_SECONDS)
        return _submit(browser, _composer(browser), text, username)
    finally:
        browser.close()


def reply_comment(settings, workspace: str, post_code: str, comment_id: str, author: str, text: str) -> str:
    author = author.strip().lstrip("@")
    if not post_code or not comment_id or not text.strip():
        raise BrowserSendFailed("Komentar tujuan atau isi balasan kosong.")
    browser = _start(settings, workspace)
    try:
        page = _open_post(browser, post_code)
        browser.inspect()
        ref = reply_ref(browser.text, comment_id)
        if not ref:
            raise BrowserSendFailed("Komentar yang dibalas tidak ditemukan di postingan Instagram.")
        browser.act("click", ref=ref)
        time.sleep(1)
        browser.inspect()
        box = comment_box_ref(browser.refs)
        if not box:
            raise BrowserSendFailed("Kolom komentar Instagram tidak ditemukan.")
        mention = f"@{author}"
        reply = text.strip()
        if author and reply.lower().startswith(mention.lower()):
            reply = reply[len(mention):].strip()
        body = f"{mention} {reply}" if author else reply
        existing = next((c for c in page.comments if c.direction == "out" and _norm(c.text) == _norm(body)), None)
        if existing:
            return "openclaw:comment:" + existing.comment_id
        if author and _norm(box_value(browser.text, box)).startswith(mention.lower()):
            browser.act("type", ref=box, text=reply, slowly=True)
            browser.inspect()
            # Typing enables/changes controls and renumbers OpenClaw refs.
            # The old textbox ref may now point at a link or Post button.
            box = comment_box_ref(browser.refs)
            if not box:
                raise BrowserSendFailed("Kolom balasan berubah setelah mengetik; pesan belum dikirim.")
        if _norm(box_value(browser.text, box)) != _norm(body):
            browser.act("type", ref=box, text=body)
            browser.inspect()
            box = comment_box_ref(browser.refs)
        if not box or _norm(box_value(browser.text, box)) != _norm(body):
            raise BrowserSendFailed("Isi kolom balasan belum sesuai; pesan belum dikirim.")
        browser.act("press", key="Enter")
        return _verify(browser, body, comment_id, post_code=post_code)
    finally:
        browser.close()


def send_action(settings, workspace: str, action, source) -> str:
    if source.kind == "dm":
        return send_dm(settings, workspace, source.sender.handle, action.text)
    if action.kind == ActionKind.REPLY_COMMENT:
        return reply_comment(settings, workspace, source.meta.get("post_code") or source.post_ref or "",
                             source.comment_ref or "", source.sender.handle, action.text)
    return message_user(settings, workspace, action.recipient or source.sender.handle, action.text)
