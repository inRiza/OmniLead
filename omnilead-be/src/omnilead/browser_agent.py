"""Workspace task coordinator over the official OpenClaw browser runtime."""

import base64
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from queue import Queue
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field

from omnilead.agent_client import AgentUnavailable
from omnilead.openclaw_browser import OpenClawBrowser, OpenClawUnavailable

CHANNELS = {
    "instagram": ("https://www.instagram.com/direct/inbox/", {"www.instagram.com", "instagram.com"}),
    "facebook": ("https://www.facebook.com/messages/", {"www.facebook.com", "facebook.com", "www.messenger.com"}),
    "whatsapp": ("https://web.whatsapp.com/", {"web.whatsapp.com"}),
    "email": ("https://mail.google.com/mail/", {"mail.google.com", "accounts.google.com"}),
}
ACTIVE = {"opening", "running", "thinking", "extracting", "executing", "manual", "closing"}
_model_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="omnilead-visual-model")
_model_slots = threading.BoundedSemaphore(4)


class BrowserConflict(Exception):
    pass


class Step(BaseModel):
    model_config = {"extra": "ignore"}
    operation: Literal["click", "type", "press", "scroll", "navigate", "finish", "need_user"]
    observation: str = Field(max_length=1200)
    reason: str = Field(max_length=600)
    target_ref: str = Field(default="", max_length=80)
    x: int = Field(default=500, ge=0, le=1000)
    y: int = Field(default=500, ge=0, le=1000)
    text: str = Field(default="", max_length=4000)
    key: Literal["Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "Backspace"] = "Tab"
    direction: Literal["up", "down"] = "down"
    url: str = Field(default="", max_length=1500)
    result: str = Field(default="", max_length=6000)
    incoming_handle: str = Field(default="", max_length=200)
    incoming_name: str = Field(default="", max_length=200)
    incoming_text: str = Field(default="", max_length=8000)


def public_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))[:1500]


def allowed_navigation(url, channel):
    try:
        parts = urlsplit(url)
        return (parts.scheme == "https" and parts.hostname in CHANNELS[channel][1]
                and parts.port in (None, 443) and not parts.username and not parts.password)
    except (KeyError, ValueError):
        return False


def read_navigation(url, channel):
    import re
    if not allowed_navigation(url, channel):
        return False
    parts = urlsplit(url)
    if parts.query or (parts.fragment and channel != "email"):
        return False
    if channel == "instagram":
        return bool(re.fullmatch(r"/direct/(?:inbox|requests|t/[0-9]+)/?", parts.path))
    if channel == "facebook":
        return bool(re.fullmatch(r"/messages(?:/t/[a-zA-Z0-9._-]+)?/?", parts.path))
    return channel == "email" and parts.hostname == "mail.google.com" and bool(
        re.fullmatch(r"/mail/u/[0-9]+/?", parts.path)
        and re.fullmatch(r"(?:inbox|sent|all|starred)(?:/[a-zA-Z0-9]+)?", parts.fragment))


class BrowserActor:
    def __init__(self, workspace, channel, settings, agent, store):
        self.workspace, self.channel, self.settings = workspace, channel, settings
        self.agent, self.store = agent, store
        self.lock, self.cancel = threading.RLock(), threading.Event()
        self.commands = Queue(maxsize=4)
        self.browser = None
        self.pending_guard = None
        self.deadline, self.business_context = 0, {}
        self.state = {"status": "opening", "engine": "openclaw", "headless": settings.browser_headless, "channel": channel, "task": "",
            "account_label": "", "image_base64": "", "image_revision": 0, "page_url": "",
            "pending": None, "observation": "", "result": "", "error": "", "steps": 0,
            "history": [], "extracted": None}
        self.thread = threading.Thread(target=self._worker, daemon=True, name="omnilead-openclaw-task")
        self.thread.start()
        self.commands.put(self._open)

    def snapshot(self):
        with self.lock:
            return {**self.state, "history": list(self.state["history"])}

    def update(self, **changes):
        with self.lock:
            self.state.update(changes)

    def record(self, operation, label):
        with self.lock:
            history = self.state["history"]
            history.append({"id": uuid.uuid4().hex, "at": time.time(), "operation": operation, "label": label[:800]})
            del history[:-60]

    def _worker(self):
        while True:
            command = self.commands.get()
            try:
                command()
            except Exception as exc:
                message = str(exc) if isinstance(exc, (BrowserConflict, AgentUnavailable, OpenClawUnavailable)) else "Langkah browser belum berhasil. Perbarui layar atau buka kembali sesi."
                if not self.cancel.is_set():
                    self.update(status="error", pending=None, error=message)
                    self.record("error", message)
            finally:
                self.commands.task_done()
            if command == self._close:
                break

    def _call_model(self, method, payload):
        if not _model_slots.acquire(blocking=False):
            raise BrowserConflict("Planner visual sedang sibuk. Tunggu sebentar sebelum mencoba kembali.")
        try:
            future = _model_workers.submit(method, payload)
        except Exception:
            _model_slots.release()
            raise
        future.add_done_callback(lambda _: _model_slots.release())
        while not future.done():
            if self.cancel.is_set():
                future.cancel()
                raise BrowserConflict("Tugas dihentikan pemilik.")
            time.sleep(0.1)
        return future.result()

    def _open(self):
        self.browser = OpenClawBrowser(self.settings, self.workspace, self.channel)
        self.browser.open(CHANNELS[self.channel][0])
        if self.cancel.is_set():
            return
        self._capture()
        self.update(status="ready")
        self.record("openclaw", "Profil browser resmi OpenClaw dibuka. Pemilik dapat login melalui kontrol manual atau jendela browser lokal.")

    def reopen(self):
        with self.lock:
            if self.state["status"] not in {"error", "stopped"} or self.commands.unfinished_tasks:
                raise BrowserConflict("Hentikan atau tunggu tugas browser sebelum membuka ulang.")
            self.cancel.clear()
            self.update(status="opening", pending=None, error="", image_base64="", page_url="",
                        result="", observation="", extracted=None, task="", steps=0)
            self.commands.put_nowait(self._reopen)

    def _reopen(self):
        if self.browser:
            try:
                self.browser.close()
            except OpenClawUnavailable:
                pass
        self.browser = None
        self._open()

    def _capture(self):
        if self.browser is None:
            raise BrowserConflict("Buka browser dahulu.")
        if not allowed_navigation(self.browser.current_url(), self.channel):
            raise BrowserConflict("Kembali ke halaman kanal yang dipilih sebelum melanjutkan tugas.")
        image = self.browser.capture()
        if not allowed_navigation(self.browser.url, self.channel):
            raise BrowserConflict("Halaman berubah ke luar kanal. Kembali ke halaman kanal dahulu.")
        self.update(image_base64=base64.b64encode(image).decode(), page_url=public_url(self.browser.url),
                    image_revision=self.state["image_revision"] + 1)
        return image

    def _guard(self):
        if self.cancel.is_set():
            raise BrowserConflict("Tugas dihentikan pemilik.")
        settings = self.store.get_settings()
        if settings.paused or self.channel in settings.disabled_channels:
            raise BrowserConflict("Agent atau kanal sedang dijeda.")
        if time.monotonic() > self.deadline:
            raise BrowserConflict("Batas waktu tugas tercapai. Tinjau layar sebelum memulai tugas baru.")

    def _idle(self):
        if self.state["status"] in ACTIVE or self.commands.unfinished_tasks:
            raise BrowserConflict("Tunggu langkah yang sedang berjalan atau hentikan tugas dahulu.")
        if self.browser is None:
            raise BrowserConflict("Buka browser dahulu.")

    def run(self, task, account_label, context):
        with self.lock:
            self._idle()
            if self.state["status"] == "awaiting_approval":
                raise BrowserConflict("Setujui atau hentikan usulan yang sedang ditampilkan dahulu.")
            self.cancel.clear()
            self.deadline, self.business_context = time.monotonic() + 300, context
            self.update(status="running", task=task, account_label=account_label, pending=None,
                        error="", result="", observation="", steps=0, extracted=None)
            self.commands.put_nowait(self._advance)

    def capture(self):
        with self.lock:
            self._idle()
            if self.state["status"] == "needs_user":
                self.update(result="")
            self.update(status="running", pending=None, error="")
            self.commands.put_nowait(self._refresh)

    def _refresh(self):
        self._capture()
        self.update(status="ready")

    def manual(self, command):
        """Explicit owner input, kept out of model context, task history and audit text."""
        with self.lock:
            self._idle()
            if self.state["pending"]:
                raise BrowserConflict("Hentikan usulan agen sebelum mengambil kontrol manual.")
            if command.image_revision != self.state["image_revision"]:
                raise BrowserConflict("Layar sudah berubah. Gunakan screenshot terbaru.")
            guard = {"url": self.browser.url, "fingerprint": self.browser.fingerprint}
            self.cancel.clear()
            self.update(status="manual", error="", extracted=None)
            self.commands.put_nowait(lambda: self._manual(command, guard))

    def _manual(self, command, guard):
        try:
            self._manual_input(command, guard)
        finally:
            command.text = ""

    def _manual_input(self, command, guard):
        if self.cancel.is_set():
            return
        if command.operation == "inbox":
            self.browser.navigate(CHANNELS[self.channel][0])
        else:
            self.browser.inspect()
            if (not allowed_navigation(self.browser.url, self.channel) or self.browser.url != guard["url"]
                    or self.browser.fingerprint != guard["fingerprint"]):
                raise BrowserConflict("Tampilan berubah sebelum input manual. Perbarui layar dan coba kembali.")
            if self.cancel.is_set():
                return
            if command.operation == "click":
                self.browser.act("clickCoords", x=min(1279, round(command.x * 1280 / 1000)),
                                 y=min(799, round(command.y * 800 / 1000)))
            elif command.operation == "type":
                self.browser.act("insertText", text=command.text)
            elif command.operation == "press":
                self.browser.act("press", key=command.key)
        # Only the operation name is retained. Password/OTP text never enters a model call.
        self.store.audit("browser_manual", f"OpenClaw {command.operation}: input langsung pemilik", actor="owner", channel=self.channel)
        self._capture()
        if not self.cancel.is_set():
            self.update(status="ready")

    def extract(self):
        with self.lock:
            self._idle()
            if self.state["status"] == "awaiting_approval":
                raise BrowserConflict("Selesaikan atau hentikan usulan langkah dahulu.")
            settings = self.store.get_settings()
            if settings.paused or self.channel in settings.disabled_channels:
                raise BrowserConflict("Agent atau kanal sedang dijeda.")
            self.cancel.clear()
            self.update(status="extracting", error="", extracted=None, result="", observation="")
            self.commands.put_nowait(self._extract)

    def _extract(self):
        image = self._capture()
        observed = self.browser.url
        if self.browser.login_required():
            self.update(status="needs_user", result="Selesaikan login dan buka percakapan pelanggan dahulu.")
            return
        message = self._call_model(self.agent.extract, {"image_base64": base64.b64encode(image).decode(),
            "mime_type": "image/jpeg", "channel": self.channel})
        if self.cancel.is_set():
            return
        if self.browser.current_url() != observed:
            raise BrowserConflict("Halaman berubah saat dibaca. Baca ulang layar sebelum mengimpor.")
        self.update(status="ready", extracted={"id": uuid.uuid4().hex,
            "handle": str(message.get("handle") or "")[:200], "name": str(message.get("name") or "")[:200],
            "text": str(message.get("text") or "")[:10000], "page_url": public_url(observed)})
        self.record("extract", "Pesan layar dibaca; pemilik perlu mengonfirmasi pengirim dan isi sebelum masuk Workspace.")

    def _advance(self):
        while not self.cancel.is_set():
            self._guard()
            if self.state["steps"] >= 12:
                self.update(status="needs_user", result="Batas 12 langkah tercapai. Tinjau layar sebelum membuat tugas baru.")
                return
            image = self._capture()
            observed = self.browser.url
            if self.browser.login_required():
                self.update(status="needs_user", pending=None, result="Selesaikan login langsung pada browser, lalu jalankan tugas kembali.")
                return
            self.update(status="thinking")
            self.record("observe", "Screenshot dan snapshot OpenClaw dikirim ke planner untuk menentukan satu langkah berikutnya.")
            step = Step.model_validate(self._call_model(self.agent.browser_plan, {
                "image_base64": base64.b64encode(image).decode(), "page_snapshot": self.browser.text,
                "task": self.state["task"], "account_label": self.state["account_label"], "channel": self.channel,
                "page_url": public_url(observed), "context": self.business_context, "history": self.state["history"][-20:]}))
            if self.cancel.is_set():
                return
            self._guard()
            if self.browser.current_url() != observed:
                raise BrowserConflict("Halaman berubah saat diamati. Jalankan tugas kembali dari layar terbaru.")
            self.update(observation=step.observation)
            if step.operation in {"finish", "need_user"}:
                if step.operation == "finish" and step.incoming_handle.strip() and step.incoming_text.strip():
                    self.update(extracted={"id": uuid.uuid4().hex, "handle": step.incoming_handle,
                        "name": step.incoming_name, "text": step.incoming_text, "page_url": public_url(observed)})
                self.update(status="done" if step.operation == "finish" else "needs_user", result=step.result or step.reason, pending=None)
                self.record(step.operation, step.reason)
                return
            if step.operation == "scroll":
                self.browser.act("press", key="PageDown" if step.direction == "down" else "PageUp")
                self._stepped("scroll", step.reason)
                continue
            if step.operation == "navigate":
                if not allowed_navigation(step.url, self.channel):
                    raise BrowserConflict("Usulan navigasi berada di luar kanal yang dipilih.")
                if read_navigation(step.url, self.channel):
                    self.browser.navigate(step.url)
                    self._stepped("navigate", "OpenClaw membuka tautan inbox atau percakapan yang dikenali.")
                    continue
            elif not step.target_ref or step.target_ref not in self.browser.refs:
                raise BrowserConflict("Planner belum memilih referensi OpenClaw yang valid. Jalankan tugas kembali.")
            if step.operation == "type" and (not step.text or any(c in step.text for c in "\r\n\x00")):
                raise BrowserConflict("Usulan ketikan harus satu baris, tanpa tombol kirim.")
            # Refresh both screenshot and refs before presenting a proposal.
            previous = self.browser.fingerprint
            self._capture()
            if self.browser.fingerprint != previous:
                raise BrowserConflict("Tampilan berubah saat usulan disiapkan. Jalankan tugas kembali.")
            target = self.browser.target(step.target_ref)
            if target.get("password"):
                raise BrowserConflict("Field rahasia harus diisi pemilik langsung pada browser.")
            self.pending_guard = {"url": observed, "target": target, "expires": time.monotonic() + 120}
            self.update(status="awaiting_approval", pending={**step.model_dump(), "id": uuid.uuid4().hex,
                                                           "target_label": target["label"]})
            self.record("proposal", step.reason)
            return

    def _stepped(self, operation, reason):
        self.update(steps=self.state["steps"] + 1)
        self.record(operation, reason)
        time.sleep(0.3)

    def approve(self, proposal_id):
        with self.lock:
            pending = self.state["pending"]
            if self.state["status"] != "awaiting_approval" or not pending or pending["id"] != proposal_id:
                raise BrowserConflict("Usulan sudah berubah atau tidak menunggu persetujuan.")
            self.update(status="executing", pending=None)
            self.commands.put_nowait(lambda: self._execute(pending))

    def _execute(self, pending):
        self._guard()
        settings = self.store.get_settings()
        if settings.dry_run:
            raise BrowserConflict("Mode simulasi aktif; input browser tidak dijalankan.")
        if sum(self.store.count_audit_since(kind, self.channel, timedelta(hours=1))
               for kind in ("browser_action", "executed")) >= settings.rate_limit_per_hour:
            raise BrowserConflict("Batas aksi per jam tercapai. Tinjau Pengaturan Agen.")
        step, guard = Step.model_validate(pending), self.pending_guard
        self.browser.inspect()
        if (not guard or time.monotonic() > guard["expires"] or self.browser.url != guard["url"]
                or self.browser.target(step.target_ref) != guard["target"]):
            raise BrowserConflict("Halaman/sasaran berubah atau persetujuan kedaluwarsa. Jalankan tugas kembali.")
        if self.browser.login_required():
            raise BrowserConflict("Login atau pemeriksaan akun memerlukan tindakan langsung pemilik.")
        self._guard()
        if step.operation == "click":
            self.browser.act("click", ref=step.target_ref)
        elif step.operation == "type":
            self.browser.act("type", ref=step.target_ref, text=step.text, submit=False)
        elif step.operation == "press":
            self.browser.act("click", ref=step.target_ref)
            self.browser.act("press", key=step.key)
        elif step.operation == "navigate":
            if not allowed_navigation(step.url, self.channel):
                raise BrowserConflict("Navigasi tidak diizinkan.")
            self.browser.navigate(step.url)
        self.store.audit("browser_action", f"OpenClaw {step.operation}: langkah disetujui pemilik", actor="owner", channel=self.channel)
        self._stepped(step.operation, step.reason)
        if not self.cancel.is_set():
            self._advance()

    def stop(self):
        with self.lock:
            if self.state["status"] in {"closing", "closed"}:
                return
            self.cancel.set()
            self.update(status="stopped", pending=None)
            self.record("stop", "Tugas dihentikan pemilik; langkah baru tidak dijalankan.")

    def close(self):
        with self.lock:
            if self.state["status"] in {"closing", "closed"}:
                return
            self.cancel.set()
            self.update(status="closing", pending=None, image_base64="")
            self.commands.put_nowait(self._close)

    def _close(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            self.browser, self.business_context, self.pending_guard = None, {}, None
            self.update(status="closed", pending=None, image_base64="", history=[], result="", task="", observation="",
                        extracted=None, page_url="", account_label="", error="", steps=0)


class BrowserManager:
    def __init__(self):
        self.lock, self.actors = threading.Lock(), {}

    def get(self, workspace):
        with self.lock:
            return self.actors.get(workspace)

    def open(self, workspace, channel, settings, agent, store):
        with self.lock:
            current = self.actors.get(workspace)
            if current and current.snapshot()["status"] != "closed":
                raise BrowserConflict("Tutup browser bisnis ini sebelum membuka kanal lain.")
            self.actors = {key: actor for key, actor in self.actors.items() if actor.snapshot()["status"] != "closed"}
            if len(self.actors) >= 4:
                raise BrowserConflict("Empat browser sedang aktif. Tutup satu sesi dahulu.")
            actor = BrowserActor(workspace, channel, settings, agent, store)
            self.actors[workspace] = actor
            return actor

    def shutdown(self):
        with self.lock:
            actors = list(self.actors.values())
        for actor in actors:
            actor.close()
        for actor in actors:
            actor.thread.join(timeout=2)


manager = BrowserManager()
