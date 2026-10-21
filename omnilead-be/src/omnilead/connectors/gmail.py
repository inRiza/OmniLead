"""Connector Gmail API (OAuth, mode Testing).

- Kirim: `users.messages.send`, dengan header In-Reply-To/References dan
  `threadId` agar masuk thread yang sama.
- Terima: `poll()` membaca email baru di INBOX. Push Pub/Sub cukup memicu
  `poll()`; dedup berdasarkan ID pesan ada di ingest.
- `watch()` mendaftarkan push ke topic Pub/Sub (berlaku 7 hari, perpanjang
  harian lewat Cloud Scheduler).

Kredensial berupa refresh token milik anggota tim (test user). Token tidak
pernah dikirim ke agen atau FE.

Dokumentasi: https://developers.google.com/workspace/gmail/api/guides
"""

import base64
import re
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime

import httpx

from omnilead.config import Settings
from omnilead.connectors.base import (
    ActionNotSupported,
    ChannelConnector,
    ConnectorError,
    NotConnected,
)
from omnilead.models import Capability, Channel, ChannelStatus, Comment, EventIn, Post, Sender

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://gmail.googleapis.com/gmail/v1/users"
PHONE_RE = re.compile(r"(?<!\d)(?:\+62|62|0)8[\d\s.-]{8,14}\d(?!\d)")


class GmailConnector(ChannelConnector):
    channel = Channel.EMAIL

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._s = settings
        self._client = client or httpx.Client(timeout=20.0)
        self._access_token = ""
        self._expires_at = 0.0

    @property
    def configured(self) -> bool:
        s = self._s
        return bool(s.gmail_client_id and s.gmail_client_secret and s.gmail_refresh_token)

    # --- kapabilitas ---

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                action="send_message",
                available=self.configured,
                path="official_api" if self.configured else "handoff",
                note="Balasan masuk thread yang sama.",
            ),
            Capability(action="read_comments", available=False, path=None),
            Capability(action="post_comment", available=False, path=None),
            Capability(action="reply_comment", available=False, path=None),
        ]

    def status(self) -> ChannelStatus:
        return ChannelStatus(
            channel=self.channel,
            connected=self.configured,
            detail="Terhubung (Gmail API)" if self.configured else "OAuth belum dijalankan",
            capabilities=self.capabilities(),
        )

    def list_posts(self, limit: int = 10) -> list[Post]:
        raise ActionNotSupported("email: list_posts tidak tersedia")

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        raise ActionNotSupported("email: read_comments tidak tersedia")

    def post_comment(self, post_ref: str, text: str) -> str:
        raise ActionNotSupported("email: post_comment tidak tersedia")

    def reply_comment(self, comment_ref: str, text: str) -> str:
        raise ActionNotSupported("email: reply_comment tidak tersedia")

    # --- OAuth ---

    def _token(self) -> str:
        if not self.configured:
            raise NotConnected(
                "Gmail belum terhubung: OMNILEAD_GMAIL_CLIENT_ID / _CLIENT_SECRET / _REFRESH_TOKEN kosong."
            )
        if self._access_token and time.time() < self._expires_at - 30:
            return self._access_token
        try:
            resp = self._client.post(
                TOKEN_URL,
                data={
                    "client_id": self._s.gmail_client_id,
                    "client_secret": self._s.gmail_client_secret,
                    "refresh_token": self._s.gmail_refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Google OAuth tidak terjangkau: {exc}") from exc
        body = _json(resp)
        if resp.status_code >= 400 or "access_token" not in body:
            # refresh token mode Testing kedaluwarsa ±7 hari
            raise NotConnected(
                f"Refresh token Gmail ditolak ({body.get('error', resp.status_code)}). Login ulang OAuth."
            )
        self._access_token = body["access_token"]
        self._expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._access_token

    def _call(self, method: str, path: str, **kw) -> dict:
        user = self._s.gmail_user
        try:
            resp = self._client.request(
                method,
                f"{API}/{user}/{path}",
                headers={"Authorization": f"Bearer {self._token()}"},
                **kw,
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Gmail API tidak terjangkau: {exc}") from exc
        body = _json(resp)
        if resp.status_code == 401:
            self._access_token = ""
            raise NotConnected("Token Gmail tidak valid. Login ulang OAuth.")
        if resp.status_code >= 400:
            err = body.get("error", {})
            msg = err.get("message", body) if isinstance(err, dict) else err
            raise ConnectorError(f"Gmail API error {resp.status_code}: {msg}")
        return body

    # --- kirim ---

    def send_message(
        self,
        recipient: str,
        text: str,
        comment_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        if not recipient or "@" not in recipient:
            raise ConnectorError("Alamat email penerima tidak valid")
        ctx = context or {}
        msg = EmailMessage()
        msg["To"] = recipient
        subject = ctx.get("subject") or "Tindak lanjut"
        msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if ctx.get("rfc_message_id"):
            msg["In-Reply-To"] = ctx["rfc_message_id"]
            msg["References"] = ctx["rfc_message_id"]
        msg.set_content(text)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        payload: dict = {"raw": raw}
        if ctx.get("thread_id"):
            payload["threadId"] = ctx["thread_id"]
        body = self._call("POST", "messages/send", json=payload)
        if "id" not in body:
            raise ConnectorError(f"Respons Gmail tanpa ID: {body}")
        return body["id"]

    def profile(self) -> dict:
        """Akun Gmail yang terhubung (users.getProfile). Baca-saja, untuk cek koneksi."""
        return self._call("GET", "profile")

    # --- terima ---

    def poll(self, max_results: int = 10, query: str = "in:inbox newer_than:2d") -> list[EventIn]:
        """Baca email masuk terbaru. Dedup dilakukan ingest berdasarkan ID pesan."""
        listing = self._call("GET", "messages", params={"q": query, "maxResults": max_results})
        me = self._call("GET", "profile").get("emailAddress", "").lower()
        events: list[EventIn] = []
        for ref in listing.get("messages", []):
            full = self._call("GET", f"messages/{ref['id']}", params={"format": "full"})
            ev = parse_message(full)
            if ev and (ev.sender.email or "").lower() != me:
                events.append(ev)
        return events

    def watch(self) -> dict:
        topic = self._s.gmail_pubsub_topic
        if not topic:
            raise ConnectorError("OMNILEAD_GMAIL_PUBSUB_TOPIC kosong")
        return self._call("POST", "watch", json={"topicName": topic, "labelIds": ["INBOX"]})


def _json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        raise ConnectorError(f"Respons non-JSON: {resp.text[:200]}")


def _b64(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _text_of(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _b64(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        found = _text_of(part)
        if found:
            return found
    return ""


def parse_message(full: dict) -> EventIn | None:
    """Ubah respons `messages.get` (format=full) menjadi EventIn."""
    headers = {h["name"].lower(): h["value"] for h in full.get("payload", {}).get("headers", [])}
    name, addr = parseaddr(headers.get("from", ""))
    body = _text_of(full.get("payload", {})).strip()
    if not addr or not body:
        return None
    phone_match = PHONE_RE.search(body)
    ts = None
    try:
        ts = parsedate_to_datetime(headers["date"]) if "date" in headers else None
    except (TypeError, ValueError):
        ts = None
    if ts is None and full.get("internalDate"):
        ts = datetime.fromtimestamp(int(full["internalDate"]) / 1000, tz=timezone.utc)
    return EventIn(
        channel=Channel.EMAIL,
        kind="email",
        external_id=full["id"],
        sender=Sender(
            handle=addr, name=name or None, email=addr,
            phone=re.sub(r"[\s.-]", "", phone_match.group(0)) if phone_match else None,
        ),
        text=body[:4000],
        ts=ts,
        meta={
            "thread_id": full.get("threadId"),
            "rfc_message_id": headers.get("message-id"),
            "subject": headers.get("subject"),
        },
    )
