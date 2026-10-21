"""Connector LinkedIn.

LinkedIn membedakan dua hal secara tegas:

- MENULIS (post & komentar atas nama member): lewat "Share on LinkedIn"
  resmi, self-serve, scope w_member_social. Ini yang dipakai executor untuk
  mengirim komentar setelah disetujui.
- MEMBACA komentar & DM post pribadi: TIDAK ADA API publik (r_member_social
  tertutup). Maka read_comments ditandai tidak tersedia, dan pesan masuk
  ditangani lewat handoff manual (modul handoff.py): pengguna menempel teks,
  agen menyusun draf, lalu pengguna mengirim sendiri.

Dokumentasi:
- Share on LinkedIn: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- Comments API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api

Catatan: endpoint komentar member memakai /rest/socialActions dengan header
LinkedIn-Version. Bodi persisnya bisa berubah antar versi API, jadi verifikasi
saat setup (lihat README, bagian "Spike LinkedIn jam pertama").
"""

import json

import httpx

from omnilead.config import Settings
from omnilead.connectors.base import (
    ActionNotSupported,
    ChannelConnector,
    ConnectorError,
    NotConnected,
)
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


class LinkedInConnector(ChannelConnector):
    channel = Channel.LINKEDIN

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._settings = settings
        self._client = client or httpx.Client(timeout=15.0)
        self._token: str | None = None
        self._person_urn: str | None = None
        self._load_token()

    # --- token OAuth (disimpan oleh alur /auth/linkedin) ---

    def _load_token(self) -> None:
        path = self._settings.linkedin_token_path
        if path.exists():
            data = json.loads(path.read_text())
            self._token = data.get("access_token")
            self._person_urn = data.get("person_urn")

    def _require_token(self) -> None:
        if not self._token or not self._person_urn:
            raise NotConnected(
                "LinkedIn belum terhubung: jalankan alur OAuth /auth/linkedin "
                "untuk mendapat access_token dan person URN."
            )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self._settings.linkedin_api_version,
            "Content-Type": "application/json",
        }

    # --- kapabilitas ---

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                action="list_posts",
                available=False,
                note="Membaca feed/post pribadi tidak tersedia di API resmi.",
            ),
            Capability(
                action="read_comments",
                available=False,
                path="handoff",
                note="Tidak ada API baca komentar pribadi; masuk lewat handoff.",
            ),
            Capability(
                action="post_comment",
                available=True,
                path="official_api",
                note="Share on LinkedIn (w_member_social).",
            ),
            Capability(
                action="reply_comment",
                available=True,
                path="official_api",
                note="Balasan komentar via socialActions.",
            ),
        ]

    def status(self) -> ChannelStatus:
        connected = bool(self._token and self._person_urn)
        detail = (
            "Terhubung (Share on LinkedIn)"
            if connected
            else "OAuth belum dijalankan"
        )
        return ChannelStatus(
            channel=self.channel,
            connected=connected,
            detail=detail,
            capabilities=self.capabilities(),
        )

    # --- baca: tidak didukung, arahkan ke handoff ---

    def list_posts(self, limit: int = 10) -> list[Post]:
        raise ActionNotSupported(
            "LinkedIn tidak menyediakan API daftar post pribadi."
        )

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        raise ActionNotSupported(
            "Komentar LinkedIn masuk lewat handoff manual, bukan API."
        )

    # --- tulis: Share on LinkedIn resmi ---

    def post_comment(self, post_ref: str, text: str) -> str:
        """Komentari sebuah post. post_ref adalah URN activity/share/ugcPost."""
        self._require_token()
        url = f"https://api.linkedin.com/rest/socialActions/{post_ref}/comments"
        payload = {
            "actor": self._person_urn,
            "message": {"text": text},
        }
        resp = self._client.post(url, headers=self._headers(), json=payload)
        return self._comment_id(resp)

    def reply_comment(self, comment_ref: str, text: str) -> str:
        """Balas komentar. comment_ref memuat URN parent + id komentar."""
        self._require_token()
        parent_urn = _parent_from_comment(comment_ref)
        url = f"https://api.linkedin.com/rest/socialActions/{parent_urn}/comments"
        payload = {
            "actor": self._person_urn,
            "message": {"text": text},
            "parentComment": comment_ref,
        }
        resp = self._client.post(url, headers=self._headers(), json=payload)
        return self._comment_id(resp)

    @staticmethod
    def _comment_id(resp: httpx.Response) -> str:
        if resp.status_code >= 400:
            raise ConnectorError(
                f"LinkedIn socialActions error {resp.status_code}: {resp.text[:200]}"
            )
        # id komentar ada di header X-RestLi-Id atau di body.
        rid = resp.headers.get("x-restli-id")
        if rid:
            return rid
        try:
            return resp.json().get("$URN") or resp.json().get("id", "")
        except ValueError:
            return ""


def _parent_from_comment(comment_ref: str) -> str:
    """Ambil URN parent dari URN komentar komposit.

    Contoh: urn:li:comment:(urn:li:activity:123,456) -> urn:li:activity:123
    """
    if "(" in comment_ref and "," in comment_ref:
        inner = comment_ref.split("(", 1)[1]
        return inner.split(",", 1)[0]
    return comment_ref
