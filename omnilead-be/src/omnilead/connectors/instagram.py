"""Connector Instagram lewat Graph API resmi.

Akun Professional (Business/Creator) milik tim, Standard Access, tanpa App
Review. Izin: instagram_business_manage_comments (komentar) dan
instagram_business_manage_messages (DM, tidak dipakai di versi ini).

Dokumentasi:
- Komentar & moderasi: https://developers.facebook.com/docs/instagram-platform/comment-moderation
- Graph API reference: https://developers.facebook.com/docs/instagram-platform

Semua panggilan tulis (post_comment, reply_comment) hanya dipanggil oleh
executor SETELAH disetujui manusia, tidak pernah oleh agen langsung.
"""

from datetime import datetime

import httpx

from omnilead.config import Settings
from omnilead.connectors.base import ChannelConnector, ConnectorError, NotConnected, TransientError, error_for_status
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


DM_MAX_BYTES = 1000


class InstagramConnector(ChannelConnector):
    channel = Channel.INSTAGRAM

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self._user_id = settings.instagram_user_id
        self._token = settings.instagram_access_token
        # Instagram API with Instagram Login: host graph.instagram.com,
        # izin instagram_business_*, tidak perlu Facebook Page.
        self._base = (
            f"{settings.instagram_api_host}/{settings.instagram_graph_version}"
        )
        self._client = client or httpx.Client(timeout=15.0)

    # --- infrastruktur ---

    def _require_token(self) -> None:
        if not self._user_id or not self._token:
            raise NotConnected(
                "Instagram belum terhubung: OMNILEAD_INSTAGRAM_USER_ID / "
                "OMNILEAD_INSTAGRAM_ACCESS_TOKEN kosong."
            )

    def _get(self, path: str, params: dict) -> dict:
        self._require_token()
        params = {**params, "access_token": self._token}
        try:
            resp = self._client.get(f"{self._base}/{path}", params=params)
        except httpx.HTTPError as exc:
            raise TransientError(f"Graph API tidak terjangkau: {exc}") from exc
        return self._unwrap(resp)

    def _post(self, path: str, data: dict) -> dict:
        self._require_token()
        data = {**data, "access_token": self._token}
        try:
            resp = self._client.post(f"{self._base}/{path}", data=data)
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
                raise NotConnected("Akses Instagram berakhir atau dicabut")
            raise error_for_status(
                resp.status_code,
                f"Graph API error {resp.status_code}: "
                f"{err.get('message', body)} (code {err.get('code')})",
            )
        return body

    # --- kapabilitas ---

    def capabilities(self) -> list[Capability]:
        connected = bool(self._user_id and self._token)
        p = "official_api" if connected else "handoff"
        return [
            Capability(action="list_posts", available=connected, path=p),
            Capability(action="read_comments", available=connected, path=p),
            Capability(action="post_comment", available=connected, path=p),
            Capability(
                action="reply_comment",
                available=connected,
                path=p,
                note="Balasan publik atas komentar di media sendiri.",
            ),
            Capability(
                action="send_message",
                available=bool(self._user_id and self._token),
                path=p if (self._user_id and self._token) else "handoff",
                note="DM (jendela 24 jam, maks 1.000 byte) atau private reply atas komentar (7 hari, sekali).",
            ),
        ]

    def status(self) -> ChannelStatus:
        connected = bool(self._user_id and self._token)
        detail = "Terhubung (Instagram API)" if connected else "Hubungkan akun Instagram Business atau Creator"
        return ChannelStatus(
            channel=self.channel,
            connected=connected,
            detail=detail,
            capabilities=self.capabilities(),
        )

    # --- baca ---

    def user_profile(self, user_id: str) -> dict:
        body = self._get(user_id, {"fields": "name,username"})
        return {"name": body.get("name"), "username": body.get("username")}

    def recent_messages(self, conversations: int = 20, per_conversation: int = 20) -> list[dict]:
        data = self._get(
            f"{self._user_id}/conversations",
            {
                "platform": "instagram",
                "limit": conversations,
                "fields": f"id,updated_time,messages.limit({per_conversation}){{id,from,to,message,created_time}}",
            },
        )
        out: list[dict] = []
        for thread in data.get("data", []):
            for msg in (thread.get("messages") or {}).get("data", []):
                sender = msg.get("from") or {}
                text = msg.get("message")
                if not msg.get("id") or not isinstance(text, str) or not text.strip():
                    continue
                if str(sender.get("id", "")) == str(self._user_id):
                    continue
                out.append({
                    "mid": str(msg["id"]),
                    "thread_id": str(thread.get("id", "")),
                    "sender_id": str(sender.get("id", "")),
                    "username": sender.get("username"),
                    "text": text,
                    "ts": _parse_ts(msg.get("created_time")),
                })
        return out

    def recent_comments(self, posts: int = 10, per_post: int = 25) -> list[Comment]:
        data = self._get(
            f"{self._user_id}/media",
            {"limit": posts, "fields": f"id,comments.limit({per_post}){{id,text,username,timestamp,from}}"},
        )
        out: list[Comment] = []
        for media in data.get("data", []):
            for item in (media.get("comments") or {}).get("data", []):
                text = item.get("text")
                if not item.get("id") or not isinstance(text, str) or not text.strip():
                    continue
                if str((item.get("from") or {}).get("id", "")) == str(self._user_id):
                    continue
                out.append(Comment(
                    id=str(item["id"]), channel=self.channel, post_ref=str(media["id"]),
                    author_handle=item.get("username") or (item.get("from") or {}).get("username", ""),
                    text=text, created_at=_parse_ts(item.get("timestamp")),
                ))
        return out

    def list_posts(self, limit: int = 10) -> list[Post]:
        data = self._get(
            f"{self._user_id}/media",
            {"fields": "id,permalink,caption,timestamp,comments_count", "limit": limit},
        )
        posts: list[Post] = []
        for item in data.get("data", []):
            posts.append(
                Post(
                    id=item["id"],
                    channel=self.channel,
                    url=item.get("permalink"),
                    caption=item.get("caption"),
                    created_at=_parse_ts(item.get("timestamp")),
                    comment_count=item.get("comments_count"),
                )
            )
        return posts

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        data = self._get(
            f"{post_ref}/comments",
            {"fields": "id,text,username,timestamp,parent_id", "limit": limit},
        )
        comments: list[Comment] = []
        for item in data.get("data", []):
            comments.append(
                Comment(
                    id=item["id"],
                    channel=self.channel,
                    post_ref=post_ref,
                    author_handle=item.get("username", ""),
                    text=item.get("text", ""),
                    created_at=_parse_ts(item.get("timestamp")),
                    parent_id=item.get("parent_id"),
                )
            )
        return comments

    # --- tulis (dipanggil executor setelah Setujui) ---

    def post_comment(self, post_ref: str, text: str) -> str:
        body = self._post(f"{post_ref}/comments", {"message": text})
        return body["id"]

    def send_message(
        self,
        recipient: str,
        text: str,
        comment_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        """DM, atau private reply bila `comment_ref` diberikan."""
        if len(text.encode("utf-8")) > DM_MAX_BYTES:
            raise ConnectorError(f"Teks DM melebihi {DM_MAX_BYTES} byte")
        self._require_token()
        target = {"comment_id": comment_ref} if comment_ref else {"id": recipient}
        resp = self._client.post(
            f"{self._base}/{self._user_id}/messages",
            params={"access_token": self._token},
            json={"recipient": target, "message": {"text": text}},
        )
        body = self._unwrap(resp)
        ref = body.get("message_id") or body.get("id")
        if not ref:
            raise ConnectorError(f"Respons Instagram tanpa ID pesan: {body}")
        return ref

    def reply_comment(self, comment_ref: str, text: str) -> str:
        # Balasan ke komentar: POST ke /{comment-id}/replies
        body = self._post(f"{comment_ref}/replies", {"message": text})
        return body["id"]


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Format Graph API: 2026-10-21T08:30:00+0000
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None
