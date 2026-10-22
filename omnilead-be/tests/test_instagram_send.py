import pytest

from omnilead import instagram_send
from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.instagram_send import BrowserSendFailed, composer_ref, send_dm, thread_ref
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
            FakeBrowser.sent.append((fields["ref"], fields["text"], fields["submit"]))

    def read_text(self):
        return " ".join(t for _, t, _ in FakeBrowser.sent) if FakeBrowser.shown else ""

    def close(self):
        pass


@pytest.fixture
def browser(monkeypatch):
    FakeBrowser.sent = []
    FakeBrowser.shown = True
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
                    lambda name, text: calls.append((name, text)) or "openclaw:abc").execute(_approved(store, event))
    assert done.status == ActionStatus.EXECUTED and done.result_ref == "openclaw:abc"
    assert calls == [("usagi", "Boleh kak")] and writer.posted == []


def test_executor_marks_openclaw_failure_as_failed(store):
    event = _openclaw_dm(store)

    def broken(name, text):
        raise BrowserSendFailed("Kolom pesan Instagram tidak ditemukan.")

    done = Executor(FakeRegistry({Channel.INSTAGRAM: FakeConnector(Channel.INSTAGRAM, can_write=True)}), store,
                    broken).execute(_approved(store, event))
    assert done.status == ActionStatus.FAILED and "Kolom pesan" in done.error
