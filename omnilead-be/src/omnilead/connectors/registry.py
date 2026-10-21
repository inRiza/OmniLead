"""Registry connector: satu tempat untuk mengambil connector per kanal."""

from omnilead.config import Settings
from omnilead.connectors.base import ActionNotSupported, ChannelConnector
from omnilead.connectors.gmail import GmailConnector
from omnilead.connectors.instagram import InstagramConnector
from omnilead.connectors.linkedin import LinkedInConnector
from omnilead.connectors.whatsapp import WhatsAppConnector
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post


class NullConnector(ChannelConnector):
    """Kanal tanpa integrasi API (WhatsApp, email, TikTok saat ini).

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
    def __init__(self, settings: Settings):
        self._connectors: dict[Channel, ChannelConnector] = {
            Channel.INSTAGRAM: InstagramConnector(settings),
            Channel.LINKEDIN: LinkedInConnector(settings),
            Channel.WHATSAPP: WhatsAppConnector(settings),
            Channel.EMAIL: GmailConnector(settings),
        }
        for ch in Channel:
            self._connectors.setdefault(ch, NullConnector(ch))

    def get(self, channel: Channel) -> ChannelConnector:
        return self._connectors.get(channel) or NullConnector(channel)

    def gmail(self) -> GmailConnector | None:
        c = self._connectors.get(Channel.EMAIL)
        return c if isinstance(c, GmailConnector) else None

    def all(self) -> list[ChannelConnector]:
        return list(self._connectors.values())
