import hashlib
import re
import time

from omnilead.instagram_snapshot import folder_ref, thread_ref
from omnilead.instagram_sync import DIALOGS, FOLDERS, INBOX_URL, SETTLE_SECONDS
from omnilead.openclaw_browser import BrowserSendFailed, OpenClawBrowser

COMPOSER = {"message", "message...", "pesan", "pesan...", "kirim pesan...", "write a message..."}


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


def send_dm(settings, workspace: str, name: str, text: str) -> str:
    if not name.strip() or not text.strip():
        raise BrowserSendFailed("Penerima atau isi pesan kosong.")
    browser = OpenClawBrowser(settings, workspace, "instagram")
    try:
        browser.open(INBOX_URL)
        time.sleep(SETTLE_SECONDS)
        browser.inspect()
        if browser.login_required():
            raise BrowserSendFailed("Sesi Instagram di browser agen belum masuk. Masuk dulu lalu kirim ulang.")
        browser.dismiss(*DIALOGS)
        time.sleep(1)
        if not _open_thread(browser, name):
            raise BrowserSendFailed(f"Percakapan dengan {name} tidak ditemukan di kotak masuk Instagram.")
        browser.inspect()
        box = composer_ref(browser.refs)
        if not box:
            raise BrowserSendFailed("Kolom pesan Instagram tidak ditemukan.")
        browser.act("type", ref=box, text=text, submit=True)
        time.sleep(SETTLE_SECONDS)
        probe = _norm(text.splitlines()[0])[:40]
        if probe not in _norm(browser.read_text()):
            raise BrowserSendFailed("Pesan sudah diketik tetapi belum terlihat terkirim di Instagram.")
        return "openclaw:" + hashlib.sha256(f"{name}|{text}|{time.time()}".encode()).hexdigest()[:24]
    finally:
        browser.close()
