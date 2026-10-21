"""Registry connector: satu tempat untuk mengambil connector per kanal."""

from omnilead.config import Settings
from omnilead.connectors.base import ActionNotSupported, ChannelConnector, NotConnected
import httpx
from omnilead.connectors.gmail import GmailConnector
from omnilead.connectors.instagram import InstagramConnector
from omnilead.connectors.whatsapp import WhatsAppConnector
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


class NullConnector(ChannelConnector):
    """Kanal aktif yang belum memiliki connector API.

    Semua aksi ditandai tidak tersedia, sehingga executor memakai handoff dan
    tidak berpura-pura terhubung.
    """

    _ACTIONS = ("list_posts", "read_comments", "post_comment", "reply_comment", "send_message")

    def __init__(self, channel: Channel):
        self.channel = channel

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                action=a, available=False, path="handoff",
                note="Integrasi API belum aktif; kirim manual (Salin & buka).",
            )
            for a in self._ACTIONS
        ]

    def status(self) -> ChannelStatus:
        return ChannelStatus(
            channel=self.channel,
            connected=False,
            detail="Belum terhubung ke API",
            capabilities=self.capabilities(),
        )

    def list_posts(self, limit: int = 10) -> list[Post]:
        raise ActionNotSupported(f"{self.channel.value}: list_posts tidak tersedia")

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        raise ActionNotSupported(f"{self.channel.value}: read_comments tidak tersedia")

    def post_comment(self, post_ref: str, text: str) -> str:
        raise ActionNotSupported(f"{self.channel.value}: post_comment tidak tersedia")

    def reply_comment(self, comment_ref: str, text: str) -> str:
        raise ActionNotSupported(f"{self.channel.value}: reply_comment tidak tersedia")


class Registry:
    def __init__(self, settings: Settings, client: httpx.Client | None = None, on_auth_error=None):
        self._connectors: dict[Channel, ChannelConnector] = {
            Channel.INSTAGRAM: InstagramConnector(settings, client),
            Channel.WHATSAPP: WhatsAppConnector(settings, client),
            Channel.EMAIL: GmailConnector(settings, client),
        }
        if on_auth_error:
            self._connectors = {ch: AuthAwareConnector(c, on_auth_error) for ch, c in self._connectors.items()}
        for ch in Channel:
            self._connectors.setdefault(ch, NullConnector(ch))

    def get(self, channel: Channel) -> ChannelConnector:
        return self._connectors.get(channel) or NullConnector(channel)

    def gmail(self) -> GmailConnector | None:
        c = self._connectors.get(Channel.EMAIL)
        if isinstance(c, AuthAwareConnector):
            return c  # delegates poll/watch while tracking expired grants
        return c if isinstance(c, GmailConnector) else None

    def all(self) -> list[ChannelConnector]:
        return list(self._connectors.values())


class AuthAwareConnector(ChannelConnector):
    """Record revoked credentials without leaking tokens into error responses."""

    def __init__(self, connector, on_auth_error):
        self.inner = connector
        self.channel = connector.channel
        self.on_auth_error = on_auth_error

    def _call(self, name, *args, **kwargs):
        try:
            return getattr(self.inner, name)(*args, **kwargs)
        except NotConnected:
            self.on_auth_error(self.channel)
            raise NotConnected("Akses akun berakhir atau dicabut. Hubungkan ulang melalui halaman Integrasi.") from None

    @property
    def configured(self):
        return getattr(self.inner, "configured", False)

    def capabilities(self):
        return self.inner.capabilities()

    def status(self):
        return self.inner.status()

    def list_posts(self, limit=10):
        return self._call("list_posts", limit=limit)

    def read_comments(self, post_ref, limit=50):
        return self._call("read_comments", post_ref, limit=limit)

    def post_comment(self, post_ref, text):
        return self._call("post_comment", post_ref, text)

    def reply_comment(self, comment_ref, text):
        return self._call("reply_comment", comment_ref, text)

    def send_message(self, recipient, text, comment_ref=None, context=None):
        return self._call("send_message", recipient, text, comment_ref, context)

    def poll(self, *args, **kwargs):
        return self._call("poll", *args, **kwargs)

    def watch(self):
        return self._call("watch")
