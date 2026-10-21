"""Connector WhatsApp Cloud API (nomor uji, terbatas).

Hanya kirim teks bebas (dalam jendela 24 jam, dicek executor via `windows.py`).
Pesan masuk datang lewat webhook (`api/webhooks.py`). Pesan keluar dipanggil
executor SETELAH disetujui manusia.

Dokumentasi: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

import httpx

from omnilead.config import Settings
from omnilead.connectors.base import (
    ActionNotSupported,
    ChannelConnector,
    ConnectorError,
    NotConnected,
)
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


class WhatsAppConnector(ChannelConnector):
    channel = Channel.WHATSAPP

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._phone_id = settings.whatsapp_phone_number_id
        self._token = settings.whatsapp_access_token
        self._base = f"https://graph.facebook.com/{settings.whatsapp_graph_version}"
        self._client = client or httpx.Client(timeout=15.0)

    @property
    def configured(self) -> bool:
        return bool(self._phone_id and self._token)

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                action="send_message",
                available=self.configured,
                path="official_api" if self.configured else "handoff",
                note="Teks bebas hanya dalam 24 jam sejak pesan masuk pelanggan.",
            ),
            Capability(action="read_comments", available=False, path=None),
            Capability(action="post_comment", available=False, path=None),
            Capability(action="reply_comment", available=False, path=None),
        ]

    def status(self) -> ChannelStatus:
        return ChannelStatus(
            channel=self.channel,
            connected=self.configured,
            detail="Terhubung (Cloud API, nomor uji)" if self.configured else "Token belum diisi",
            capabilities=self.capabilities(),
        )

    def list_posts(self, limit: int = 10) -> list[Post]:
        raise ActionNotSupported("whatsapp: list_posts tidak tersedia")

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        raise ActionNotSupported("whatsapp: read_comments tidak tersedia")

    def post_comment(self, post_ref: str, text: str) -> str:
        raise ActionNotSupported("whatsapp: post_comment tidak tersedia")

    def reply_comment(self, comment_ref: str, text: str) -> str:
        raise ActionNotSupported("whatsapp: reply_comment tidak tersedia")

    def send_message(
        self,
        recipient: str,
        text: str,
        comment_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        if not self.configured:
            raise NotConnected(
                "WhatsApp belum terhubung: OMNILEAD_WHATSAPP_PHONE_NUMBER_ID / "
                "OMNILEAD_WHATSAPP_ACCESS_TOKEN kosong."
            )
        digits = "".join(ch for ch in recipient if ch.isdigit())
        if not digits:
            raise ConnectorError("Nomor WhatsApp penerima tidak valid")
        try:
            resp = self._client.post(
                f"{self._base}/{self._phone_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": digits,
                    "type": "text",
                    "text": {"body": text, "preview_url": False},
                },
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"WhatsApp tidak terjangkau: {exc}") from exc
        try:
            body = resp.json()
        except ValueError:
            raise ConnectorError(f"Respons non-JSON dari WhatsApp: {resp.text[:200]}")
        if resp.status_code == 401:
            raise NotConnected("Token WhatsApp kedaluwarsa atau tidak valid")
        if resp.status_code >= 400 or "error" in body:
            err = body.get("error", {})
            raise ConnectorError(
                f"WhatsApp error {resp.status_code}: {err.get('message', body)} (code {err.get('code')})"
            )
        try:
            return body["messages"][0]["id"]
        except (KeyError, IndexError):
            raise ConnectorError(f"Respons WhatsApp tanpa ID pesan: {body}")
