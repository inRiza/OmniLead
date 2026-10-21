"""Registry connector: satu tempat untuk mengambil connector per kanal."""

from omnilead.config import Settings
from omnilead.connectors.base import ChannelConnector
from omnilead.connectors.instagram import InstagramConnector
from omnilead.models import Channel


class Registry:
    def __init__(self, settings: Settings):
        self._connectors: dict[Channel, ChannelConnector] = {
            Channel.INSTAGRAM: InstagramConnector(settings),
        }

    def get(self, channel: Channel) -> ChannelConnector:
        return self._connectors[channel]

    def all(self) -> list[ChannelConnector]:
        return list(self._connectors.values())
