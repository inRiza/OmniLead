import pytest

from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.connectors.base import ChannelConnector
from omnilead.connectors.registry import Registry
from omnilead.models import Capability, Channel, ChannelStatus, Comment, Post
from omnilead.store import Store


@pytest.fixture(autouse=True)
def legacy_auth_mode(monkeypatch):
    """Existing connector/CRM tests explicitly use the local demo auth mode."""
    from omnilead.config import get_settings
    monkeypatch.setenv("OMNILEAD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeConnector(ChannelConnector):
    """Connector palsu untuk tes, mencatat panggilan tulis."""

    def __init__(self, channel: Channel, can_write: bool):
        self.channel = channel
        self._can_write = can_write
        self.posted: list[tuple[str, str]] = []

    def capabilities(self) -> list[Capability]:
        return [
            Capability(action="read_comments", available=True, path="official_api"),
            Capability(
                action="post_comment",
                available=self._can_write,
                path="official_api" if self._can_write else "handoff",
            ),
            Capability(
                action="reply_comment",
                available=self._can_write,
                path="official_api" if self._can_write else "handoff",
            ),
            Capability(
                action="send_message",
                available=self._can_write,
                path="official_api" if self._can_write else "handoff",
            ),
        ]

    def status(self) -> ChannelStatus:
        return ChannelStatus(
            channel=self.channel,
            connected=True,
            capabilities=self.capabilities(),
        )

    def list_posts(self, limit: int = 10) -> list[Post]:
        return []

    def read_comments(self, post_ref: str, limit: int = 50) -> list[Comment]:
        return [
            Comment(
                id="c1",
                channel=self.channel,
                post_ref=post_ref,
                author_handle="pelanggan",
                text="harganya berapa kak?",
            )
        ]

    def post_comment(self, post_ref: str, text: str) -> str:
        self.posted.append((post_ref, text))
        return "posted-id-1"

    def reply_comment(self, comment_ref: str, text: str) -> str:
        self.posted.append((comment_ref, text))
        return "reply-id-1"

    def send_message(self, recipient, text, comment_ref=None, context=None):
        self.posted.append((comment_ref or recipient, text))
        return "msg-id-1"


class FakeRegistry(Registry):
    def __init__(self, connectors):
        self._connectors = connectors


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")


@pytest.fixture
def ig():
    return FakeConnector(Channel.INSTAGRAM, can_write=True)


@pytest.fixture
def registry(ig):
    return FakeRegistry({Channel.INSTAGRAM: ig})


@pytest.fixture
def ig_no_write():
    # Kanal tanpa kemampuan tulis via API -> executor harus jatuh ke handoff
    return FakeConnector(Channel.INSTAGRAM, can_write=False)


@pytest.fixture
def handoff_executor(ig_no_write, store):
    return Executor(FakeRegistry({Channel.INSTAGRAM: ig_no_write}), store)


@pytest.fixture
def queue(store):
    return ApprovalQueue(store)


@pytest.fixture
def executor(registry, store):
    return Executor(registry, store)
