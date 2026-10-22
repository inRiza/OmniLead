"""Connector Facebook Page lewat Graph API dan Messenger Platform resmi.

Polanya sama dengan connector Instagram. Bedanya:
- host `graph.facebook.com` dan token yang dipakai adalah Page access token;
- membalas komentar = membuat komentar baru di bawah komentar itu
  (`POST /{comment-id}/comments`), bukan `/replies`;
- Messenger dikirim lewat `POST /{page-id}/messages` dengan
  `messaging_type=RESPONSE` (dalam jendela 24 jam) dan teks maks 2.000 karakter.

Izin: pages_show_list, pages_messaging, pages_read_engagement,
pages_read_user_content, pages_manage_engagement, pages_manage_metadata.

Dokumentasi:
- Messenger Send API: https://developers.facebook.com/docs/messenger-platform/reference/send-api
- Private replies: https://developers.facebook.com/docs/messenger-platform/discovery/private-replies
- Komentar Page: https://developers.facebook.com/docs/graph-api/reference/object/comments

Semua panggilan tulis hanya dipanggil oleh executor SETELAH disetujui manusia.
"""

from datetime import datetime

import httpx

from omnilead.config import Settings
from omnilead.connectors.base import ChannelConnector, ConnectorError, NotConnected, TransientError, error_for_status
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


MESSAGE_MAX_CHARS = 2000


class FacebookConnector(ChannelConnector):
    channel = Channel.FACEBOOK

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._page_id = settings.facebook_page_id
        self._token = settings.facebook_page_access_token
        self._base = f"https://graph.facebook.com/{settings.facebook_graph_version}"
        self._client = client or httpx.Client(timeout=15.0)

    # --- infrastruktur ---

    @property
    def _connected(self) -> bool:
        return bool(self._page_id and self._token)

    def _require_token(self) -> None:
        if not self._connected:
            raise NotConnected(
                "Facebook belum terhubung: OMNILEAD_FACEBOOK_PAGE_ID / "
                "OMNILEAD_FACEBOOK_PAGE_ACCESS_TOKEN kosong."
            )

    def _get(self, path: str, params: dict) -> dict:
        self._require_token()
        try:
            resp = self._client.get(f"{self._base}/{path}", params={**params, "access_token": self._token})
        except httpx.HTTPError as exc:
            raise TransientError(f"Graph API tidak terjangkau: {exc}") from exc
        return self._unwrap(resp)

    def _post(self, path: str, data: dict) -> dict:
        self._require_token()
        try:
            resp = self._client.post(f"{self._base}/{path}", data={**data, "access_token": self._token})
        except httpx.HTTPError as exc:
            raise TransientError(f"Graph API tidak terjangkau: {exc}") from exc
        return self._unwrap(resp)

    @staticmethod
    def _unwrap(resp: httpx.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            raise ConnectorError(f"Respons non-JSON dari Graph API: {resp.text[:200]}")
        if resp.status_code >= 400 or "error" in body:
            err = body.get("error", {})
            if resp.status_code == 401 or err.get("code") == 190:
                raise NotConnected("Akses Facebook Page berakhir atau dicabut")
            raise error_for_status(
                resp.status_code,
                f"Graph API error {resp.status_code}: "
                f"{err.get('message', body)} (code {err.get('code')})",
            )
        return body

    # --- kapabilitas ---

    def capabilities(self) -> list[Capability]:
        connected = self._connected
        p = "official_api" if connected else "handoff"
        return [
            Capability(action="list_posts", available=connected, path=p),
            Capability(action="read_comments", available=connected, path=p),
            Capability(action="post_comment", available=connected, path=p),
            Capability(
                action="reply_comment",
                available=connected,
                path=p,
                note="Balasan publik atas komentar di post Page sendiri.",
            ),
            Capability(
                action="send_message",
                available=connected,
                path=p,
                note="Messenger (jendela 24 jam, maks 2.000 karakter) atau private reply atas komentar (7 hari, sekali).",
            ),
        ]

    def status(self) -> ChannelStatus:
        detail = "Terhubung (Facebook Page)" if self._connected else "Hubungkan Facebook Page bisnis"
        return ChannelStatus(
            channel=self.channel,
            connected=self._connected,
            detail=detail,
            capabilities=self.capabilities(),
        )

    # --- baca ---

    def user_profile(self, user_id: str) -> dict:
        body = self._get(user_id, {"fields": "first_name,last_name"})
        name = " ".join(p for p in (body.get("first_name"), body.get("last_name")) if p)
        return {"name": name or None, "username": None}

    def list_posts(self, limit: int = 10) -> list[Post]:
        data = self._get(
            f"{self._page_id}/posts",
            {"fields": "id,permalink_url,message,created_time,comments.summary(true).limit(0)", "limit": limit},
        )
        posts: list[Post] = []
        for item in data.get("data", []):
            posts.append(
                Post(
                    id=item["id"],
                    channel=self.channel,
                    url=item.get("permalink_url"),
                    caption=item.get("message"),
                    created_at=_parse_ts(item.get("created_time")),
                    comment_count=((item.get("comments") or {}).get("summary") or {}).get("total_count"),
                )
            )
        return posts

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        data = self._get(
            f"{post_ref}/comments",
            {"fields": "id,message,from,created_time,parent", "limit": limit},
        )
        comments: list[Comment] = []
        for item in data.get("data", []):
            author = item.get("from") or {}
            comments.append(
                Comment(
                    id=item["id"],
                    channel=self.channel,
                    post_ref=post_ref,
                    author_handle=author.get("name") or author.get("id", ""),
                    text=item.get("message", ""),
                    created_at=_parse_ts(item.get("created_time")),
                    parent_id=(item.get("parent") or {}).get("id"),
                )
            )
        return comments

    # --- tulis (dipanggil executor setelah Setujui) ---

    def post_comment(self, post_ref: str, text: str) -> str:
        return self._post(f"{post_ref}/comments", {"message": text})["id"]

    def reply_comment(self, comment_ref: str, text: str) -> str:
        # Di Facebook, balasan adalah komentar di bawah komentar asal.
        return self._post(f"{comment_ref}/comments", {"message": text})["id"]

    def send_message(
        self,
        recipient: str,
        text: str,
        comment_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        """Pesan Messenger, atau private reply bila `comment_ref` diberikan."""
        if len(text) > MESSAGE_MAX_CHARS:
            raise ConnectorError(f"Teks Messenger melebihi {MESSAGE_MAX_CHARS} karakter")
        self._require_token()
        target = {"comment_id": comment_ref} if comment_ref else {"id": recipient}
        resp = self._client.post(
            f"{self._base}/{self._page_id}/messages",
            params={"access_token": self._token},
            json={"recipient": target, "messaging_type": "RESPONSE", "message": {"text": text}},
        )
        body = self._unwrap(resp)
        ref = body.get("message_id") or body.get("id")
        if not ref:
            raise ConnectorError(f"Respons Messenger tanpa ID pesan: {body}")
        return ref


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Format Graph API: 2026-10-21T08:30:00+0000
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None
