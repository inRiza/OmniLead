import pytest

from omnilead import instagram_send
from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.instagram_send import BrowserSendFailed, composer_ref, send_dm, thread_ref
from omnilead.openclaw_browser import OpenClawUnavailable
from omnilead.instagram_snapshot import threads as parse_threads
from omnilead.models import ActionKind, ActionStatus, Channel, EventIn, ProposedAction, Sender
from tests.conftest import FakeConnector, FakeRegistry

INBOX_REFS = {
    "e20": {"role": "tab", "name": "Primary"},
    "e21": {"role": "tab", "name": "General"},
    "e27": {"role": "button", "name": "user-profile-picture allosteric site halo halo \xa0 13 hours ago"},
    "e28": {"role": "button", "name": "user-profile-picture usagi Hai kak >< maaf ganggu"},
}


def test_thread_ref_matches_whole_name_only():
    assert thread_ref(INBOX_REFS, "allosteric site") == "e27"
    assert thread_ref(INBOX_REFS, "usagi") == "e28"
    assert thread_ref(INBOX_REFS, "usa") == ""
    assert composer_ref({"e9": {"role": "textbox", "name": "Search"}, "e50": {"role": "textbox", "name": "Message"}}) == "e50"


def test_system_previews_are_not_messages():
    snap = """- main
  - button "user-profile-picture Niko Niko sent an attachment. 2h" [ref=e1]
    - image "user-profile-picture"
        - StaticText "Niko"
        - StaticText "Niko sent an attachment."
  - button "user-profile-picture hijab scarves 3 new messages" [ref=e2]
    - image "user-profile-picture"
        - StaticText "hijab scarves"
        - StaticText "3 new messages"
  - button "user-profile-picture Seni Liked a message" [ref=e3]
    - image "user-profile-picture"
        - StaticText "Seni"
        - StaticText "Liked a message"
  - button "user-profile-picture usagi boleh minta pfp?" [ref=e4]
    - image "user-profile-picture"
        - StaticText "usagi"
        - StaticText "boleh minta pfp?"
"""
    assert [t.name for t in parse_threads(snap)] == ["usagi"]


class FakeBrowser:
    sent: list = []
    shown = True
    type_errors: list = []
    type_calls = 0

    def __init__(self, settings, workspace, channel):
        self.url = "https://www.instagram.com/direct/inbox/"
        self.refs = {}
        self.page = "inbox"

    def open(self, url):
        pass

    def inspect(self):
        self.refs = {"e60": {"role": "textbox", "name": "Message"}} if self.page == "thread" else dict(INBOX_REFS)

    def login_required(self):
        return False

    def dismiss(self, *labels):
        return False

    def act(self, kind, **fields):
        if kind == "click" and fields["ref"] == "e28":
            self.page = "thread"
        if kind == "type":
            FakeBrowser.type_calls += 1
            if FakeBrowser.type_errors:
                raise FakeBrowser.type_errors.pop(0)
            FakeBrowser.sent.append((fields["ref"], fields["text"], fields["submit"]))

    def read_text(self):
        return " ".join(t for _, t, _ in FakeBrowser.sent) if FakeBrowser.shown else ""

    def close(self):
        pass


@pytest.fixture
def browser(monkeypatch):
    FakeBrowser.sent = []
    FakeBrowser.shown = True
    FakeBrowser.type_errors = []
    FakeBrowser.type_calls = 0
    monkeypatch.setattr(instagram_send, "OpenClawBrowser", FakeBrowser)
    monkeypatch.setattr(instagram_send.time, "sleep", lambda s: None)
    return FakeBrowser


def test_send_dm_types_into_thread_and_verifies(browser):
    ref = send_dm(None, "ws1", "usagi", "Boleh kak, kirim detailnya ya")
    assert ref.startswith("openclaw:") and browser.sent == [("e60", "Boleh kak, kirim detailnya ya", True)]


def test_send_dm_reports_missing_thread_and_unconfirmed(browser):
    with pytest.raises(BrowserSendFailed, match="tidak ditemukan"):
        send_dm(None, "ws1", "orang lain", "halo")
    browser.shown = False
    with pytest.raises(BrowserSendFailed, match="belum terlihat terkirim"):
        send_dm(None, "ws1", "usagi", "halo")


TIMEOUT = "OpenClaw menolak POST /act: TimeoutError: locator.type: Timeout 10000ms exceeded."


def test_send_dm_retries_when_the_composer_is_not_actionable_yet(browser):
    browser.type_errors = [OpenClawUnavailable(TIMEOUT)]
    ref = send_dm(None, "ws1", "usagi", "Boleh kak")
    assert ref.startswith("openclaw:") and browser.type_calls == 2
    assert browser.sent == [("e60", "Boleh kak", True)]  # terkirim sekali saja


def test_send_dm_does_not_retry_gateway_failures(browser):
    browser.type_errors = [OpenClawUnavailable("Gateway tidak merespons.")]
    with pytest.raises(OpenClawUnavailable, match="Gateway"):
        send_dm(None, "ws1", "usagi", "Boleh kak")
    assert browser.type_calls == 1 and browser.sent == []


def test_send_dm_gives_up_after_repeated_timeouts_without_sending(browser):
    browser.type_errors = [OpenClawUnavailable(TIMEOUT)] * 5
    with pytest.raises(OpenClawUnavailable, match="Timeout"):
        send_dm(None, "ws1", "usagi", "Boleh kak")
    assert browser.type_calls == instagram_send.ACT_ATTEMPTS and browser.sent == []


def _openclaw_dm(store):
    from omnilead.ingest import IngestService

    ev = EventIn(channel=Channel.INSTAGRAM, kind="dm", external_id="openclaw:x", sender=Sender(handle="usagi", name="usagi"),
                 text="boleh minta pfp?", meta={"source": "openclaw_text", "handoff_only": True})
    event, _ = IngestService(store, ApprovalQueue(store), None).ingest(ev, analyze=False)
    return event


def _approved(store, event):
    queue = ApprovalQueue(store)
    return queue.approve(queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.SEND_MESSAGE,
                                                      text="Boleh kak", recipient="usagi", event_id=event.id)).id)


def test_executor_sends_openclaw_dm_in_test_mode(store):
    event = _openclaw_dm(store)
    calls = []
    writer = FakeConnector(Channel.INSTAGRAM, can_write=True)
    done = Executor(FakeRegistry({Channel.INSTAGRAM: writer}), store,
                    lambda action, source: calls.append((source.sender.handle, action.text)) or "openclaw:abc"
                    ).execute(_approved(store, event))
    assert done.status == ActionStatus.EXECUTED and done.result_ref == "openclaw:abc"
    assert calls == [("usagi", "Boleh kak")] and writer.posted == []


def test_executor_marks_openclaw_failure_as_failed(store):
    event = _openclaw_dm(store)

    def broken(action, source):
        raise BrowserSendFailed("Kolom pesan Instagram tidak ditemukan.")

    done = Executor(FakeRegistry({Channel.INSTAGRAM: FakeConnector(Channel.INSTAGRAM, can_write=True)}), store,
                    broken).execute(_approved(store, event))
    assert done.status == ActionStatus.FAILED and "Kolom pesan" in done.error


POST_PAGE = """- main
  - link "dapurbunda.id" [ref=e126] [url=https://www.instagram.com/dapurbunda.id/]
  - time
    - StaticText "2d"
  - StaticText "Nasi box ayam bakar"
    - link "sari.home" [ref=e127] [url=https://www.instagram.com/sari.home/]
      - link "8m" [ref=e33] [url=https://www.instagram.com/p/DQabc123/c/1801/]
      - StaticText "masih ada kak?"
    - button "Reply" [ref=e34]
    - link "andi" [ref=e128] [url=https://www.instagram.com/andi/]
      - link "1h" [ref=e35] [url=https://www.instagram.com/p/DQabc123/c/1802/]
      - StaticText "lucu"
    - button "Reply" [ref=e36]
"""


class SocialBrowser:
    typed: list = []
    clicked: list = []
    pressed: list = []
    appends = True
    value = ""

    def __init__(self, settings, workspace, channel):
        self.url = ""
        self.refs = {}
        self.text = ""
        self.page = "inbox"

    def open(self, url):
        pass

    def login_required(self):
        return False

    def dismiss(self, *labels):
        return False

    def navigate(self, url):
        self.page = "post"

    def inspect(self):
        self.text = POST_PAGE if self.page.startswith("post") else ""
        if self.page == "post_reply":
            editor = "e50" if SocialBrowser.value == "@sari.home " else "e51"
            self.text += f'- textbox "Add a comment…" [ref={editor}] value="{SocialBrowser.value}"\n'

        self.refs = {
            "inbox": {"e22": {"role": "textbox", "name": "Search"}},
            "searched": {"e21": {"role": "button", "name": "User avatar Anggita Najmi gitaanaj You both follow x"},
                         "e24": {"role": "button", "name": "User avatar gitaanaja"}},
            "thread": {"e67": {"role": "textbox", "name": "Message..."}},
            "post": {"e34": {"role": "button", "name": "Reply"}},
            "post_reply": {"e50": {"role": "textbox", "name": "Add a comment…"}},
        }.get(self.page, {})
        if self.page == "post_reply" and SocialBrowser.value != "@sari.home ":
            self.refs = {"e50": {"role": "link", "name": "Other post"},
                         "e51": {"role": "textbox", "name": "Add a comment…"}}

    def act(self, kind, **fields):
        if kind == "click":
            SocialBrowser.clicked.append(fields["ref"])
            self.page = {"e21": "thread", "e34": "post_reply"}.get(fields["ref"], self.page)
            if fields["ref"] == "e34":
                SocialBrowser.value = "@sari.home "
        if kind == "press":
            SocialBrowser.pressed.append(fields["key"])
            SocialBrowser.typed.append(("e50", SocialBrowser.value, True))
        if kind == "type":
            if fields["ref"] in ("e50", "e51"):
                assert self.refs[fields["ref"]]["role"] == "textbox", "Cannot type into a stale ref"
                slow = fields.get("slowly") and SocialBrowser.appends
                SocialBrowser.value = SocialBrowser.value + fields["text"] if slow else fields["text"]
                return
            SocialBrowser.typed.append((fields["ref"], fields["text"], fields["submit"]))
            if fields["ref"] == "e22":
                self.page = "searched"

    def read_text(self):
        snapshot = POST_PAGE + " ".join(t for _, t, _ in SocialBrowser.typed)
        if self.page == "post_reply" and SocialBrowser.pressed:
            snapshot += ('\n    - link "dapurbunda.id" [url=https://www.instagram.com/dapurbunda.id/]\n'
                         '      - link "now" [url=https://www.instagram.com/p/DQabc123/c/1901/]\n'
                         f'      - StaticText "{SocialBrowser.value}"\n')
        return snapshot

    def close(self):
        pass


@pytest.fixture
def social(monkeypatch):
    SocialBrowser.typed, SocialBrowser.clicked, SocialBrowser.pressed = [], [], []
    SocialBrowser.appends, SocialBrowser.value = True, ""
    monkeypatch.setattr(instagram_send, "OpenClawBrowser", SocialBrowser)
    monkeypatch.setattr(instagram_send.time, "sleep", lambda s: None)
    from omnilead import instagram_sync
    monkeypatch.setattr(instagram_sync.time, "sleep", lambda s: None)
    return SocialBrowser


def test_reply_comment_threads_under_the_right_comment(social):
    ref = instagram_send.reply_comment(None, "ws1", "DQabc123", "1801", "sari.home", "Masih ada kak, mau berapa box?")
    assert ref.startswith("openclaw:") and social.clicked == ["e34"] and social.pressed == ["Enter"]
    assert social.typed == [("e50", "@sari.home Masih ada kak, mau berapa box?", True)]

    social.typed, social.appends = [], False
    instagram_send.reply_comment(None, "ws1", "DQabc123", "1801", "sari.home", "@sari.home Masih kak")
    assert social.typed == [("e50", "@sari.home Masih kak", True)]
    with pytest.raises(BrowserSendFailed, match="tidak ditemukan"):
        instagram_send.reply_comment(None, "ws1", "DQabc123", "9999", "x", "halo")


def test_private_reply_opens_dm_by_exact_username(social):
    instagram_send.message_user(None, "ws1", "@gitaanaj", "Halo kak, ini detailnya ya")
    assert social.clicked == ["e21"]
    assert social.typed == [("e22", "gitaanaj", False), ("e67", "Halo kak, ini detailnya ya", True)]


def test_executor_routes_openclaw_comment_reply_to_browser(store):
    from omnilead.ingest import IngestService

    ev = EventIn(channel=Channel.INSTAGRAM, kind="comment", external_id="1801", sender=Sender(handle="sari.home"),
                 text="masih ada kak?", post_ref="DQabc123", comment_ref="1801",
                 meta={"source": "openclaw_text", "post_code": "DQabc123"})
    event, _ = IngestService(store, ApprovalQueue(store), None).ingest(ev, analyze=False)
    queue = ApprovalQueue(store)
    calls = []
    writer = FakeConnector(Channel.INSTAGRAM, can_write=True)
    for kind in (ActionKind.REPLY_COMMENT, ActionKind.SEND_MESSAGE):
        action = queue.approve(queue.propose(ProposedAction(
            channel=Channel.INSTAGRAM, kind=kind, text="Masih kak", recipient="sari.home", post_ref="DQabc123",
            comment_ref="1801", event_id=event.id)).id)
        done = Executor(FakeRegistry({Channel.INSTAGRAM: writer}), store,
                        lambda a, s: calls.append((a.kind, s.comment_ref)) or "openclaw:x").execute(action)
        assert done.status == ActionStatus.EXECUTED
    assert calls == [(ActionKind.REPLY_COMMENT, "1801"), (ActionKind.SEND_MESSAGE, "1801")] and writer.posted == []
