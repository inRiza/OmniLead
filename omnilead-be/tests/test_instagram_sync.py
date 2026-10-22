from datetime import datetime, timedelta, timezone

import httpx
import pytest

from omnilead import instagram_sync
from omnilead.agent_client import AgentClient
from omnilead.config import Settings
from omnilead.connectors.base import ConnectorError, NotConnected
from omnilead.connectors.instagram import InstagramConnector
from omnilead.ingest import IngestService
from omnilead.instagram_snapshot import comments as parse_comments, conversation as parse_conversation, threads as parse_threads
from omnilead.instagram_sync import record_webhook, sync_instagram
from omnilead.models import ActionKind, ActionStatus, Channel, Comment, EventIn, ProposedAction, Sender
from tests.conftest import FakeRegistry
from tests.test_ingest_api import CANNED, FakeAgent, client  # noqa: F401

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

REQUESTS = """- main
  - button "user-profile-picture Rizain F Apakah kamu buka comission? 3m Unread" [ref=e45]
    - image "user-profile-picture"
        - StaticText "Rizain F"
        - StaticText "Apakah kamu buka comission?"
        - Abbr "3 minutes ago"
          - StaticText "3m"
        - StaticText "Unread"
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


THREAD = """- main
  - link "Profile" [ref=e5] [url=https://www.instagram.com/toko.kita/]
  - main
    - link "Open the profile page of rina.toko" [ref=e24] [url=https://www.instagram.com/rina.toko/]
    - heading "Rina Toko" [ref=e29] [level=2]
    - generic
      - generic
        - article "kak mau tanya nasi box" [ref=e38] [tabindex]
          - StaticText "kak mau tanya nasi box"
          - group "Message actions"
            - button "React to message from rina.toko" [ref=e52]
            - button "Reply to message from rina.toko" [ref=e53]
      - generic
        - StaticText "Thu 1:18 AM"
        - article "Halo kak, untuk berapa orang?" [ref=e41] [tabindex]
          - StaticText "Halo kak, untuk berapa orang?"
        - group "Message actions"
          - button "React to message from toko.kita" [ref=e58]
          - button "Reply to message from toko.kita" [ref=e59]
      - generic
        - link "Open the profile page of rina.toko" [ref=e43] [url=https://www.instagram.com/rina.toko]
        - article "50 orang tgl 30" [ref=e44] [tabindex]
          - StaticText "50 orang tgl 30"
          - group "Message actions"
            - button "React to message from rina.toko" [ref=e61]
        - article "Unsupported message Use the Instagram mobile app to view this message." [ref=e46] [tabindex]
          - group "Message actions"
            - button "React to message from rina.toko" [ref=e63]
        - article "kak harga nasbox?" [ref=e45] [tabindex]
          - StaticText "kak harga nasbox?"
          - group "Message actions"
            - button "React to message from rina.toko" [ref=e62]
    - textbox "Message..." [ref=e77]
"""


def test_parse_conversation_from_thread_snapshot():
    messages = parse_conversation(THREAD)
    assert [(m.direction, m.text) for m in messages] == [
        ("in", "kak mau tanya nasi box"), ("out", "Halo kak, untuk berapa orang?"),
        ("in", "50 orang tgl 30"), ("in", "[media]"), ("in", "kak harga nasbox?"),
    ]
    assert [m.text for m in parse_conversation(THREAD, limit=2)] == ["[media]", "kak harga nasbox?"]
    assert parse_conversation(INBOX) == []


def test_folder_tabs_match_with_unread_count_and_locale():
    from omnilead.instagram_snapshot import folder_ref

    refs = {"e20": {"role": "tab", "name": "Utama"}, "e21": {"role": "tab", "name": "General (3)"},
            "e22": {"role": "tab", "name": "Request (1)"}, "e9": {"role": "link", "name": "Requests"}}
    assert [folder_ref(refs, f) for f in instagram_sync.FOLDERS] == ["e20", "e21", "e22"]


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
        elif self.page in ("primary", "rina", "general", "requests", "request_thread"):
            self.refs = {"e20": {"role": "tab", "name": "Primary"}, "e21": {"role": "tab", "name": "General"},
                         "e22": {"role": "tab", "name": "Request (1)"}}
            if self.page in ("requests", "request_thread"):
                self.refs["e45"] = {"role": "button", "name": "user-profile-picture Rizain F Apakah kamu buka comission? 3m"}
            if self.page == "request_thread":
                self.refs["e50"] = {"role": "button", "name": "Accept"}
            if self.page in ("primary", "rina"):
                self.refs["e27"] = {"role": "button", "name": "user-profile-picture Rina Toko kak harga nasbox? 11h"}
            if self.page == "rina":
                self.refs["e38"] = {"role": "article", "name": "kak mau tanya nasi box"}
        else:
            self.refs = {}

    def act(self, kind, **fields):
        FakeBrowser.log.append(("click" if kind == "click" else kind, fields["ref"]))
        self.page = {"e3": "primary", "e21": "general", "e22": "requests", "e27": "rina", "e45": "request_thread",
                     "e50": "primary"}.get(fields["ref"], self.page)

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
        return {"primary": INBOX, "rina": INBOX + THREAD, "general": GENERAL, "requests": REQUESTS,
                "request_thread": REQUESTS + THREAD.replace("rina.toko", "rizainfird"),
                "notifications": NOTIFICATIONS}.get(self.page, "")

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
    assert (result["dms"], result["comments"]) == (2, 1)  # the 2-day-old General message is history, not a new reply target
    assert ("click", "e3") in browser.log and ("click", "e21") in browser.log and ("click", "e22") in browser.log
    assert ("navigate", instagram_sync.NOTIFICATIONS_URL) in browser.log and browser.closed == 1
    assert len(agent.calls) == calls
    events = {e.text: e for e in store.list_events()}
    assert events["kak harga nasbox?"].meta["folder"] == "Primary" and events["kak harga nasbox?"].meta["unread"] is True
    assert "bisa kirim ke Bekasi?" not in events
    assert events["Apakah kamu buka comission?"].meta["folder"] == "Requests"
    assert "siap kak" not in events
    note = events["masih ada kak?"]
    assert note.kind == "comment" and note.external_id == "18129021832872344" and note.sender.handle == "sari.home"
    again = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert again["imported"] == 0 and again["duplicates"] == 3


def test_openclaw_reads_thread_history_and_sends_it_as_timeline(store, ingest, browser, agent):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    sync_instagram(store, registry, ingest, settings(browser_enabled=True, instagram_history_limit=10,
                                                     instagram_history_scrolls=2), "ws1")
    assert ("scrollIntoView", "e38") in browser.log
    event = next(e for e in store.list_events() if e.text == "kak harga nasbox?")
    assert [m["text"] for m in event.meta["conversation"]][-2:] == ["[media]", "kak harga nasbox?"]
    assert not any(e.text == "bisa kirim ke Bekasi?" for e in store.list_events())
    ingest.process(ingest.prepare(event), expected_run_id=None)
    timeline = agent.calls[-1]["lead"]["timeline"]
    assert [(t["direction"], t["text"]) for t in timeline] == [
        ("in", "kak mau tanya nasi box"), ("out", "Halo kak, untuk berapa orang?"), ("in", "50 orang tgl 30"),
        ("in", "[media]"),
    ]

    browser.log.clear()
    sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert ("click", "e27") not in browser.log


def _autonomy(store, mode):
    s = store.get_settings()
    s.autonomy = mode
    store.save_settings(s)


def test_hybrid_asks_before_opening_unread_or_accepting_requests(store, ingest, browser):
    _autonomy(store, "hybrid")
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert [t["name"] for t in result["pending"]["read_unread"]] == ["Rina Toko"]
    assert [t["name"] for t in result["pending"]["accept_request"]] == ["Rizain F"]
    assert ("click", "e27") not in browser.log and ("click", "e45") not in browser.log
    assert ("click", "e50") not in browser.log
    assert {e.text for e in store.list_events() if e.kind == "dm"} == set()
    assert instagram_sync.sync_status(store)["pending"] == result["pending"]

    granted = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1",
                             allow=["read_unread", "accept_request"])
    assert granted["pending"] == {} and granted["dms"] == 2
    assert ("click", "e27") in browser.log and ("click", "e50") in browser.log
    request = next(e for e in store.list_events() if e.sender.handle == "Rizain F")
    assert request.meta["accepted"] is True and request.meta["conversation"]


def test_full_access_reads_unread_and_accepts_without_asking(store, ingest, browser):
    _autonomy(store, "auto")
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["pending"] == {} and result["dms"] == 2
    assert ("click", "e27") in browser.log and ("click", "e50") in browser.log


def test_sync_route_passes_owner_permission(client, store, monkeypatch):
    calls = []
    monkeypatch.setattr("omnilead.api.routes.sync_instagram", lambda *a, **k: calls.append(k) or {"pending": {}})
    r = client.post("/instagram/sync?allow=read_unread&allow=accept_request")
    assert r.status_code == 200 and calls[-1]["allow"] == ["read_unread", "accept_request"]
    assert any(e.event == "browser_permission_granted" for e in store.list_audit(limit=10))


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
    assert result["needs_login"] and result["imported"] == 0 and "belum masuk" in result["error"]
    assert browser.closed == 1


def test_openclaw_unavailable_is_reported(store, ingest, monkeypatch):
    from omnilead.openclaw_browser import OpenClawUnavailable

    def boom(*a, **k):
        raise OpenClawUnavailable("Gateway tidak merespons")

    monkeypatch.setattr(instagram_sync, "OpenClawBrowser", boom)
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(error=NotConnected("token kosong"))})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["source"] == "none" and "Gateway OpenClaw" in result["error"] and "token kosong" in result["error"]


def test_prefer_browser_skips_meta_api(store, ingest, browser):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(messages=[msg("m-api", "dari api")])})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1", prefer_browser=True)
    assert result["source"] == "openclaw_text" and result["dms"] == 2
    assert all(e.meta.get("source") == "openclaw_text" for e in store.list_events() if e.kind == "dm")


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


def test_empty_meta_api_falls_back_to_openclaw(store, ingest, browser):
    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector()})
    result = sync_instagram(store, registry, ingest, settings(browser_enabled=True), "ws1")
    assert result["source"] == "openclaw_text" and (result["dms"], result["comments"]) == (2, 1)


def test_sync_queues_new_messages_and_analyzes_them_in_order(store, ingest, agent):
    from omnilead.analysis_state import visible_analysis_state
    from omnilead.instagram_sync import queue_analysis, run_analysis_queue

    registry = FakeRegistry({Channel.INSTAGRAM: ApiConnector(messages=[msg("m2", "kedua", minutes=1), msg("m1", "pertama", minutes=5)])})
    sync_instagram(store, registry, ingest, settings(), "legacy")
    ids = queue_analysis(store)
    assert [store.get_event(i).text for i in ids] == ["pertama", "kedua"]
    assert all(visible_analysis_state(store.get_event(i)).trace["queued"] for i in ids)
    assert queue_analysis(store) == ids
    calls = len(agent.calls)
    run_analysis_queue(store, ingest, ids)
    assert len(agent.calls) == calls + 2
    assert {store.get_event(i).status for i in ids} == {"analyzed"}
    assert queue_analysis(store) == []


def test_stale_queue_marker_is_dropped(store):
    from omnilead.analysis_state import visible_analysis_state
    from omnilead.models import Event

    old = (NOW - timedelta(minutes=30)).isoformat()
    event = Event(id="e1", channel=Channel.INSTAGRAM, kind="dm", external_id="x", sender=Sender(handle="a"), text="halo",
                  trace={"queued": True, "queued_at": old, "status": "Menunggu giliran"})
    assert visible_analysis_state(event).trace is None
