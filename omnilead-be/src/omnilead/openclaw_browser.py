"""Adapter to the official OpenClaw browser control API; no platform API tokens."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx


class OpenClawUnavailable(Exception):
    pass


class OpenClawBrowser:
    def __init__(self, settings, workspace, channel):
        endpoint = urlsplit(settings.openclaw_browser_url)
        if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"} or endpoint.username or endpoint.password:
            raise OpenClawUnavailable("Kontrol OpenClaw harus memakai alamat loopback lokal.")
        token_path = settings.openclaw_token_file.resolve()
        if not token_path.is_file():
            raise OpenClawUnavailable("Jalankan tools/openclaw/start.ps1 untuk menyiapkan OpenClaw lokal.")
        self.http = httpx.Client(base_url=settings.openclaw_browser_url.rstrip("/"), timeout=35,
            headers={"Authorization": "Bearer " + token_path.read_text().strip()}, trust_env=False)
        self.state_dir = settings.openclaw_state_dir.resolve()
        self.profile = "ol-" + hashlib.sha256(f"{workspace}:{channel}".encode()).hexdigest()[:24]
        self.headless = settings.browser_headless
        self.target_id = ""
        self.url = ""
        self.text = ""
        self.refs = {}
        self.fingerprint = ""

    def request(self, method, path, body=None, **query):
        try:
            response = self.http.request(method, path, params={"profile": self.profile, **query}, json=body,
                timeout=90 if path == "/start" else 35)
            if response.is_error:
                try:
                    reason = response.json().get("reason")
                except (ValueError, AttributeError):
                    reason = None
                if reason == "navigation_blocked":
                    raise OpenClawUnavailable("Pengaturan OpenClaw memblokir domain kanal. Pengelola perlu memperbarui izin domain browser.")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except (httpx.HTTPError, ValueError):
            raise OpenClawUnavailable("OpenClaw belum dapat menjalankan operasi browser. Periksa gateway lokal dan jendela browser.") from None

    def open(self, url):
        profiles = self.request("GET", "/profiles").get("profiles", [])
        if not any(isinstance(item, dict) and item.get("name") == self.profile for item in profiles):
            self.request("POST", "/profiles/create", {"name": self.profile, "driver": "openclaw", "color": "#f97316"})
        self.request("POST", "/start", headless=str(self.headless).lower())
        # Headed Chromium cannot inspect redirects in the native tab-creation path.
        # Open a blank tab, then use OpenClaw's guarded navigation implementation.
        tab = self.request("POST", "/tabs/open", {"url": "about:blank"})
        self.target_id = str(tab["targetId"])
        self.url = str(tab.get("url") or url)
        self.act("resize", width=1280, height=800)
        self.navigate(url)
        self.request("POST", "/tabs/focus", {"targetId": self.target_id})

    def current_url(self):
        if not self.target_id:
            raise OpenClawUnavailable("Tab kanal belum berhasil dibuka. Klik Buka ulang browser.")
        tabs = self.request("GET", "/tabs").get("tabs", [])
        tab = next((item for item in tabs if item.get("targetId") == self.target_id), None)
        if not tab:
            raise OpenClawUnavailable("Tab tugas sudah ditutup. Tutup sesi lalu buka browser kembali.")
        self.url = str(tab.get("url") or "")
        return self.url

    def inspect(self):
        data = self.request("GET", "/snapshot", targetId=self.target_id,
            format="ai", interactive="true", compact="true", urls="true", timeoutMs=15000)
        self.url = str(data.get("url") or self.url)
        self.text = str(data.get("snapshot") or "")[:24000]
        self.refs = data.get("refs") or {}
        if not isinstance(self.refs, dict):
            raise OpenClawUnavailable("Snapshot OpenClaw belum berisi referensi elemen yang didukung.")
        self.fingerprint = hashlib.sha256(json.dumps({"url": self.url, "text": self.text,
            "refs": self.refs}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def capture(self):
        self.inspect()
        response = self.request("POST", "/screenshot", {"targetId": self.target_id,
            "type": "jpeg", "fullPage": False, "timeoutMs": 15000})
        path = Path(response.get("path", "")).resolve()
        media_root = (self.state_dir / "media" / "browser").resolve()
        if not path.is_relative_to(media_root) or path.suffix.lower() not in {".jpg", ".jpeg"} or not path.is_file():
            raise OpenClawUnavailable("Lokasi screenshot OpenClaw tidak sesuai direktori runtime lokal.")
        try:
            if path.stat().st_size > 2_000_000:
                raise OpenClawUnavailable("Screenshot terlalu besar untuk planner visual.")
            image = path.read_bytes()
            if not image.startswith(b"\xff\xd8"):
                raise OpenClawUnavailable("Format screenshot OpenClaw bukan JPEG yang diharapkan.")
        finally:
            path.unlink(missing_ok=True)
        if str(response.get("url") or self.url) != self.url:
            raise OpenClawUnavailable("Halaman berubah saat screenshot dibuat. Perbarui layar.")
        return image

    def login_required(self):
        parts = urlsplit(self.url)
        return (bool(re.search(r"/(login|challenge|checkpoint|oauth|signin)(/|\.|$)", parts.path.lower()))
            or parts.hostname == "accounts.google.com"
            or bool(re.search(r"textbox.*(?:password|kata sandi|one.time|otp)|scan (?:this |the )?qr|pindai kode|log into whatsapp", self.text, re.I)))

    def target(self, ref):
        if not ref:
            return {"ref": "", "label": "Halaman kanal", "snapshot": self.fingerprint}
        item = self.refs.get(ref)
        if not isinstance(item, dict):
            raise OpenClawUnavailable("Referensi elemen sudah tidak berlaku. Jalankan tugas kembali dari layar terbaru.")
        label = str(item.get("name") or item.get("role") or ref)[:160]
        return {"ref": ref, "label": label, "descriptor": item, "snapshot": self.fingerprint,
                "password": bool(re.search(r"password|kata sandi|one.time|otp", label, re.I))}

    def act(self, kind, **fields):
        result = self.request("POST", "/act", {"kind": kind, "targetId": self.target_id,
            "timeoutMs": 10000, **fields})
        if result.get("targetId"):
            self.target_id = str(result["targetId"])
        if result.get("url"):
            self.url = str(result["url"])

    def navigate(self, url):
        result = self.request("POST", "/navigate", {"targetId": self.target_id, "url": url})
        self.target_id = str(result.get("targetId") or self.target_id)
        self.url = str(result.get("url") or url)

    def close(self):
        try:
            self.request("POST", "/stop")
        finally:
            self.http.close()
