from datetime import datetime, timedelta, timezone

import httpx
import pytest

from omnilead import instagram_sync
from omnilead.agent_client import AgentClient
from omnilead.config import Settings
from omnilead.connectors.base import ConnectorError, NotConnected
from omnilead.connectors.instagram import InstagramConnector
from omnilead.ingest import IngestService
from omnilead.instagram_snapshot import comments as parse_comments, threads as parse_threads
from omnilead.instagram_sync import record_webhook, sync_instagram
from omnilead.models import ActionKind, ActionStatus, Channel, Comment, EventIn, ProposedAction, Sender
from tests.conftest import FakeRegistry
from tests.test_ingest_api import CANNED, FakeAgent

NOW = datetime.now(timezone.utc)

INBOX = """- main
  - tab "Primary" [ref=e20] [selected]
  - tab "General" [ref=e21]
  - button "user-profile-picture Rina Toko kak harga nasbox? 11 hours ago Unread" [ref=e27]
    - image "user-profile-picture"
        - StaticText "Rina Toko"
          - InlineTextBox "Rina Toko"
        - StaticText "kak harga nasbox?"
          - InlineTextBox "kak harga nasbox?"
        - StaticText ""
        - Abbr "11 hours ago"
          - StaticText "11h"
        - StaticText "Unread"
  - button "user-profile-picture Budi You: siap kak 5 weeks ago" [ref=e28]
    - image "user-profile-picture"
        - StaticText "Budi"
        - StaticText "You: siap kak"
        - Abbr "5 weeks ago"
          - StaticText "5w"
"""

GENERAL = """- main
  - button "user-profile-picture Dodi Active 2h ago" [ref=e41]
    - image "user-profile-picture"
        - StaticText "Dodi"
        - StaticText "Active 2h ago"
  - button "user-profile-picture Maya bisa kirim ke Bekasi? 2 days ago" [ref=e40]
    - image "user-profile-picture"
        - StaticText "Maya"
        - StaticText "bisa kirim ke Bekasi?"
        - Abbr "2 days ago"
          - StaticText "2d"
"""

NOTIFICATIONS = """- generic "page" [ref=e1]
  - link "Reels" [ref=e3] [url=https://www.instagram.com/reels/]
  - main
   - heading "Today" [ref=e13] [level=1]
  - generic "sari.home commented: masih ada kak? 8m" [ref=e14] [cursor:pointer, onclick]
      - link "sari.home's profile picture" [ref=e33] [url=https://www.instagram.com/sari.home/]
        - image "sari.home's profile picture"
      - link "sari.home" [ref=e31] [url=https://www.instagram.com/sari.home/]
          - StaticText "sari.home"
      - StaticText "commented: masih ada kak?"
      - Abbr "8 minutes ago"
        - StaticText "8m"
    - link "post" [ref=e34] [url=https://www.instagram.com/dapurbunda.id/DQabc123/c/18129021832872344/]
  - generic "andi liked your post. 1h" [ref=e15]
      - link "andi" [ref=e36] [url=https://www.instagram.com/andi/]
      - StaticText "liked your post."
"""


def test_parse_threads_from_inbox_snapshot():
    rina, budi = parse_threads(INBOX)
    assert (rina.name, rina.preview, rina.unread, rina.incoming, rina.time) == ("Rina Toko", "kak harga nasbox?", True, True, "11h")
    assert (budi.incoming, budi.preview) == (False, "siap kak")


def test_parse_comments_from_notifications_snapshot():
    (c,) = parse_comments(NOTIFICATIONS)
    assert (c.username, c.text, c.comment_id, c.post_code, c.time) == ("sari.home", "masih ada kak?", "18129021832872344", "DQabc123", "8m")


class ApiConnector:
    channel = Channel.INSTAGRAM

    def __init__(self, messages=None, comments=None, error=None, comment_error=None):
        self.messages = messages or []
        self.comments = comments or []
        self.error = error
        self.comment_error = comment_error

    def recent_messages(self):
        if self.error:
            raise self.error
        return self.messages

    def recent_comments(self):
        if self.comment_error or self.error:
            raise self.comment_error or self.error
        return self.comments


@pytest.fixture
def agent():
    a = FakeAgent()
    a.response = {**CANNED, "proposals": []}
    return a


@pytest.fixture
def ingest(store, queue, agent):
    return IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)))


def msg(mid, text, sender="1789", minutes=1, username="ani.rahma"):
    return {"mid": mid, "thread_id": "t1", "sender_id": sender, "username": username, "text": text,
            "ts": NOW - timedelta(minutes=minutes)}


def comment(cid, text, author="sari.home"):
    return Comment(id=cid, channel=Channel.INSTAGRAM, post_ref="media1", author_handle=author, text=text,
                   created_at=NOW - timedelta(minutes=3))


def settings(**kw):
    return Settings(browser_enabled=kw.pop("browser_enabled", False), **kw)


def test_connector_reads_incoming_messages_only():
    def handler(request):
        assert request.url.path.endswith("/17841/conversations")
        return httpx.Response(200, json={"data": [{"id": "t1", "messages": {"data": [
            {"id": "m1", "from": {"id": "999", "username": "ani"}, "message": "harga?", "created_time": "2026-10-22T03:00:00+0000"},
            {"id": "m2", "from": {"id": "17841", "username": "toko"}, "message": "siap kak"},
        ]}}]})

    conn = InstagramConnector(Settings(instagram_user_id="17841", instagram_access_token="tok"),
                              client=httpx.Client(transport=httpx.MockTransport(handler)))
    (only,) = conn.recent_messages()
    assert only["mid"] == "m1" and only["sender_id"] == "999"


def test_connector_reads_comments_skipping_own():
    def handler(request):
        assert request.url.path.endswith("/17841/media")
        assert "comments.limit(25)" in request.url.params["fields"]
        return httpx.Response(200, json={"data": [{"id": "p1", "comments": {"data": [
            {"id": "c1", "text": "harga?", "username": "ani", "from": {"id": "999"}, "timestamp": "2026-10-22T03:00:00+0000"},
            {"id": "c2", "text": "cek DM kak", "username": "toko", "from": {"id": "17841"}},
            {"id": "c3", "text": " "},
        ]}}, {"id": "p2"}]})

    conn = InstagramConnector(Settings(instagram_user_id="17841", instagram_access_token="tok"),
                              client=httpx.Client(transport=httpx.MockTransport(handler)))
    (only,) = conn.recent_comments()
    assert (only.id, only.post_ref, only.author_handle) == ("c1", "p1", "ani")


def test_api_sync_fetches_dms_and_comments_without_running_agent(store, ingest, agent):
    ingest.ingest(EventIn(channel=Channel.INSTAGRAM, kind="dm", external_id="m1", sender=Sender(handle="1789"),
                          text="sudah lewat webhook", ts=NOW - timedelta(minutes=5)))
    calls = len(agent.calls)
    record_webhook(store, 1)
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(
        messages=[msg("m1", "sudah lewat webhook", minutes=5), msg("m2", "pesan yang hilang")],
        comments=[comment("c9", "masih ada kak?")])})
    result = sync_instagram(store, registry, ingest, settings(), "legacy")
    assert result["source"] == "meta_api" and result["error"] == ""
    assert (result["fetched"], result["imported"], result["dms"], result["comments"], result["duplicates"]) == (3, 2, 1, 1, 1)
    assert result["webhook_gap"] == 2 and not result["webhook_stale"]
    assert len(agent.calls) == calls
    events = {e.external_id: e for e in store.list_events()}
    assert events["m2"].status == "new" and events["m2"].meta["username"] == "ani.rahma"
    assert events["c9"].kind == "comment" and events["c9"].comment_ref == "c9" and events["c9"].post_ref == "media1"
    assert any(e.event == "instagram_webhook_gap" for e in store.list_audit(limit=20))
    again = sync_instagram(store, registry, ingest, settings(), "legacy")
    assert again["imported"] == 0 and again["duplicates"] == 3


def test_api_sync_matches_comment_lead_by_username(store, ingest):
    first, _ = ingest.ingest(EventIn(channel=Channel.INSTAGRAM, kind="comment", external_id="c1",
                                     sender=Sender(handle="ani.rahma"), text="info harga"))
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(messages=[msg("m9", "kak saya DM ya")])})
    sync_instagram(store, registry, ingest, settings(), "legacy")
    dm = next(e for e in store.list_events() if e.external_id == "m9")
    assert dm.lead_id == first.lead_id


def test_partial_api_failure_still_imports_and_reports(store, ingest):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(
        messages=[msg("m5", "halo")], comment_error=ConnectorError("izin komentar belum diberikan"))})
    result = sync_instagram(store, registry, ingest, settings(), "legacy")
    assert result["source"] == "meta_api" and result["dms"] == 1 and "izin komentar" in result["error"]


def test_no_api_and_browser_disabled_reports_error(store, ingest):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("Instagram belum terhubung"))})
    result = sync_instagram(store, registry, ingest, settings(), "legacy")
    assert result["source"] == "none" and "belum terhubung" in result["error"]


class FakeBrowser:
    login = False
    log: list = []
    closed = 0

    def __init__(self, settings, workspace, channel):
        assert channel == "instagram"
        self.url = ""
        self.text = ""
        self.refs = {}
        self.page = ""

    def open(self, url):
        FakeBrowser.log.append(("open", url))
        self.url = "https://www.instagram.com/accounts/login/" if FakeBrowser.login else url
        self.page = "inbox_dialog"

    def inspect(self):
        if self.page == "inbox_dialog":
            self.refs = {"e3": {"role": "button", "name": "Not Now"}}
        elif self.page == "primary":
            self.refs = {"e20": {"role": "tab", "name": "Primary"}, "e21": {"role": "tab", "name": "General"}}
        else:
            self.refs = {}

    def act(self, kind, **fields):
        FakeBrowser.log.append(("click", fields["ref"]))
        self.page = {"e3": "primary", "e21": "general"}.get(fields["ref"], self.page)

    def dismiss(self, *labels):
        self.inspect()
        if "e3" in self.refs:
            self.act("click", ref="e3")
            return True
        return False

    def navigate(self, url):
        FakeBrowser.log.append(("navigate", url))
        self.page = "notifications"

    def read_text(self):
        return {"primary": INBOX, "general": GENERAL, "notifications": NOTIFICATIONS}.get(self.page, "")

    def login_required(self):
        return FakeBrowser.login

    def close(self):
        FakeBrowser.closed += 1


@pytest.fixture
def browser(monkeypatch):
    FakeBrowser.login = False
    FakeBrowser.log = []
    FakeBrowser.closed = 0
    monkeypatch.setattr(instagram_sync, "OpenClawBrowser", FakeBrowser)
    monkeypatch.setattr(instagram_sync.time, "sleep", lambda s: None)
    return FakeBrowser


def test_openclaw_reads_primary_general_and_comment_notifications(store, ingest, browser, agent):
    calls = len(agent.calls)
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["source"] == "openclaw_text" and result["error"] == ""
    assert result["api_error"] == "token kosong"
    assert (result["dms"], result["comments"]) == (2, 1)
    assert ("click", "e3") in browser.log and ("click", "e21") in browser.log
    assert ("navigate", instagram_sync.NOTIFICATIONS_URL) in browser.log and browser.closed == 1
    assert len(agent.calls) == calls
    events = {e.text: e for e in store.list_events()}
    assert events["kak harga nasbox?"].meta["folder"] == "Primary" and events["kak harga nasbox?"].meta["unread"] is True
    assert events["bisa kirim ke Bekasi?"].meta["folder"] == "General"
    assert "siap kak" not in events
    note = events["masih ada kak?"]
    assert note.kind == "comment" and note.external_id == "18129021832872344" and note.sender.handle == "sari.home"
    again = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert again["imported"] == 0 and again["duplicates"] == 3


def test_openclaw_dm_forces_manual_send(store, ingest, browser):
    from omnilead.approvals.executor import Executor
    from omnilead.approvals.queue import ApprovalQueue
    from tests.conftest import FakeConnector

    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    dm = next(e for e in store.list_events() if e.kind == "dm")
    queue = ApprovalQueue(store)
    writer = FakeConnector(Channel.INSTAGRAM, can_write=True)
    sent = Executor(FakeRegistry({Channel.INSTAGRAM: writer}), store).execute(queue.approve(queue.propose(ProposedAction(
        channel=Channel.INSTAGRAM, kind=ActionKind.SEND_MESSAGE, text="Halo kak", recipient="x", event_id=dm.id)).id))
    assert sent.status == ActionStatus.AWAITING_MANUAL_SEND and writer.posted == []


def test_openclaw_fallback_needs_login(store, ingest, browser):
    browser.login = True
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["needs_login"] and result["imported"] == 0 and "Masuk ke Instagram" in result["error"]
    assert browser.closed == 1


def test_openclaw_unavailable_is_reported(store, ingest, monkeypatch):
    from omnilead.openclaw_browser import OpenClawUnavailable

    def boom(*a, **k):
        raise OpenClawUnavailable("Gateway OpenClaw tidak merespons")

    monkeypatch.setattr(instagram_sync, "OpenClawBrowser", boom)
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["source"] == "none" and "Gateway OpenClaw" in result["error"] and "token kosong" in result["error"]


def test_answer_later_runs_agent_on_fetched_event(store, ingest):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(messages=[msg("m7", "harga 30 pax?")])})
    sync_instagram(store, registry, ingest, settings(), "legacy")
    event = store.list_events()[0]
    assert event.status == "new" and event.trace is None

    from omnilead.analysis_state import visible_analysis_state
    assert visible_analysis_state(event, now=NOW + timedelta(hours=2)).status == "new"
    assert ingest.process(event).status == "analyzed"


def test_webhook_marks_last_seen_and_status_route(tmp_path, monkeypatch):
    import hashlib
    import hmac
    import json

    from fastapi.testclient import TestClient

    from omnilead.api import deps
    from omnilead.config import get_settings
    from omnilead.main import create_app
    from omnilead.store import Store

    monkeypatch.setenv("OMNILEAD_META_APP_SECRET", "s3cret")
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "s3cret")
    get_settings.cache_clear()
    st = Store(tmp_path / "w.db")

    class Ingest:
        store = st

        def ingest(self, event, **kw):
            return event, False

    app = create_app()
    app.dependency_overrides[deps.get_store] = lambda: st
    app.dependency_overrides[deps.get_ingest] = lambda: Ingest()
    client = TestClient(app)
    assert client.get("/instagram/sync").json()["webhook_stale"] is True
    body = json.dumps({"object": "instagram", "entry": [{"id": "1", "messaging": [{"sender": {"id": "2"}, "recipient": {"id": "1"},
        "timestamp": int(NOW.timestamp() * 1000), "message": {"mid": "x1", "text": "halo"}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    r = client.post("/webhooks/instagram", content=body, headers={"x-hub-signature-256": sig, "content-type": "application/json"})
    assert r.status_code == 200
    status = client.get("/instagram/sync").json()
    assert status["webhook_stale"] is False and status["webhook_last_event_at"]
    get_settings.cache_clear()
