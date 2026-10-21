"""Dapatkan refresh token Gmail untuk mode demo (OMNILEAD_AUTH_ENABLED=false).

Prasyarat (Google Cloud Console):
1. Aktifkan Gmail API.
2. OAuth consent screen mode Testing; tambahkan akun Gmail Anda sebagai test user.
3. Buat OAuth client tipe "Desktop app"; isi OMNILEAD_GMAIL_CLIENT_ID dan
   OMNILEAD_GMAIL_CLIENT_SECRET di omnilead-be/.env.

Jalankan dari folder omnilead-be:
    uv run python scripts/gmail_refresh_token.py

Browser terbuka untuk login Google. Setelah izin diberikan, skrip mencetak baris
OMNILEAD_GMAIL_REFRESH_TOKEN=... untuk ditempel ke .env. Access token tidak
pernah dicetak. Di mode Testing, refresh token kedaluwarsa sekitar 7 hari.
"""

import base64
import hashlib
import secrets
import socket
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from omnilead.config import Settings
from omnilead.oauth import SCOPES

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
TIMEOUT_S = 300


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    settings = Settings()
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        print("Isi dulu OMNILEAD_GMAIL_CLIENT_ID dan OMNILEAD_GMAIL_CLIENT_SECRET di .env.")
        return 1

    port = free_port()
    redirect_uri = f"http://127.0.0.1:{port}/"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)

    url = AUTH_URL + "?" + urlencode({
        "client_id": settings.gmail_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES["gmail"]),
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })

    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            query = parse_qs(urlparse(self.path).query)
            # Abaikan request lain (mis. favicon) yang bukan jawaban OAuth.
            if "code" not in query and "error" not in query:
                self.send_response(404)
                self.end_headers()
                return
            if query.get("state", [""])[0] != state:
                result["error"] = "state tidak cocok"
            elif "error" in query:
                result["error"] = query["error"][0]
            else:
                result["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Selesai. Kembali ke terminal." if "code" in result else "Gagal. Lihat terminal."
            self.wfile.write(f"<p style='font-family:sans-serif'>{msg}</p>".encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    print("Membuka browser untuk login Google. Jika tidak terbuka, salin URL ini:\n")
    print(url + "\n")
    webbrowser.open(url)
    deadline = time.monotonic() + TIMEOUT_S
    while not result:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            server.server_close()
            print("Waktu habis tanpa jawaban dari Google.")
            return 1
        server.timeout = remaining
        server.handle_request()
    server.server_close()

    if "error" in result:
        print(f"Login dibatalkan atau ditolak: {result['error']}")
        return 1

    resp = httpx.post(TOKEN_URL, data={
        "code": result["code"],
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }, timeout=20)
    body = resp.json()
    refresh = body.get("refresh_token")
    if resp.status_code >= 400 or not refresh:
        print(f"Tukar kode gagal: {body.get('error_description') or body.get('error') or resp.status_code}")
        return 1

    granted = set(body.get("scope", "").split())
    missing = set(SCOPES["gmail"]) - granted
    if missing:
        print(f"Peringatan: izin belum diberikan: {', '.join(sorted(missing))}")

    print("Berhasil. Tempel baris ini ke omnilead-be/.env:\n")
    print(f"OMNILEAD_GMAIL_REFRESH_TOKEN={refresh}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
