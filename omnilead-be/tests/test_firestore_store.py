"""Logika FirestoreStore, diuji dengan fake in-memory (bukan Firestore sungguhan)."""

from collections import namedtuple
from datetime import datetime, timedelta, timezone

import pytest

from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.models import (
    ActionKind, ActionStatus, AppSettings, Channel, Event, Lead, ProposedAction, Sender,
)
from omnilead.store_firestore import FirestoreStore

FF = namedtuple("FF", "field op value")


class Exists(Exception):
    pass


class Snap:
    def __init__(self, ref, data):
        self.reference, self._d = ref, data

    @property
    def exists(self):
        return self._d is not None

    def to_dict(self):
        return dict(self._d)


class Doc:
    def __init__(self, col, id):
        self.col, self.id = col, id

    def set(self, data):
        self.col.docs[self.id] = dict(data)

    def create(self, data):
        if self.id in self.col.docs:
            raise Exists()
        self.col.docs[self.id] = dict(data)

    def get(self):
        return Snap(self, self.col.docs.get(self.id))

    def delete(self):
        self.col.docs.pop(self.id, None)


class Col:
    def __init__(self, filters=()):
        self.docs: dict = {}
        self._filters = filters
        self._root = self

    def document(self, id):
        return Doc(self._root, id)

    def where(self, filter):
        c = Col(self._filters + (filter,))
        c._root = self._root
        return c

    def stream(self):
        for id, d in list(self._root.docs.items()):
            if all(d.get(f.field) == f.value for f in self._filters):
                yield Snap(Doc(self._root, id), d)


class FakeFirestore:
    def __init__(self):
        self.cols: dict[str, Col] = {}

    def collection(self, name):
        return self.cols.setdefault(name, Col())


@pytest.fixture
def fs(monkeypatch):
    monkeypatch.setattr("google.api_core.exceptions.AlreadyExists", Exists, raising=False)
    store = FirestoreStore(client=FakeFirestore(), field_filter=FF)
    store._already_exists = Exists
    return store


NOW = datetime.now(timezone.utc)


def prop(**kw):
    base = dict(channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT, post_ref="p", comment_ref="c", text="halo")
    base.update(kw)
    return ProposedAction(**base)


def test_actions_roundtrip_and_status_filter(fs):
    q = ApprovalQueue(fs)
    a, b = q.propose(prop()), q.propose(prop(text="dua"))
    q.reject(b.id, "salah")
    assert fs.get_action(a.id).text == "halo" and fs.get_action("none") is None
    assert [x.id for x in fs.list_actions(ActionStatus.PENDING)] == [a.id]
    assert len(fs.list_actions()) == 2
    assert "salah" in fs.get_settings().preferences  # preferensi dari penolakan tersimpan


def test_events_dedup_key_and_lead_filter(fs):
    ev = Event(id="e1", channel=Channel.WHATSAPP, kind="message", external_id="wamid.1",
               sender=Sender(handle="h"), text="hai", ts=NOW, lead_id="l1")
    fs.save_event(ev)
    fs.save_event(ev)  # menyimpan ulang event yang sama tidak error
    assert fs.find_event("whatsapp", "wamid.1").id == "e1" and fs.find_event("whatsapp", "x") is None
    clash = ev.model_copy(update={"id": "e2"})  # ID pesan sama, event lain -> ditolak
    with pytest.raises(Exists):
        fs.save_event(clash)
    assert [e.id for e in fs.list_events(lead_id="l1")] == ["e1"] and fs.list_events(lead_id="zzz") == []


def test_leads_settings_and_merge_reassign(fs, monkeypatch):
    for i, score in (("a", 10), ("b", 90)):
        fs.save_lead(Lead(id=i, name=i, score=score, created_at=NOW, updated_at=NOW))
    assert [l.id for l in fs.list_leads()] == ["b", "a"]  # skor tertinggi dulu
    fs.save_event(Event(id="e1", channel=Channel.EMAIL, kind="email", external_id="m1",
                        sender=Sender(), text="x", ts=NOW, lead_id="a"))
    fs.reassign_lead("a", "b")
    fs.delete_lead("a")
    assert fs.get_event("e1").lead_id == "b" and fs.get_lead("a") is None
    s = AppSettings(paused=True, disabled_channels=[Channel.TIKTOK])
    fs.save_settings(s)
    assert fs.get_settings().paused and fs.get_settings().disabled_channels == [Channel.TIKTOK]


def test_audit_order_filter_and_rate_count(fs):
    fs.audit("executed", "a", channel="instagram")
    fs.audit("executed", "b", channel="instagram")
    fs.audit("executed", "c", channel="whatsapp")
    entries = fs.list_audit(limit=2)
    assert [e.detail for e in entries] == ["c", "b"]  # terbaru dulu
    assert [e.detail for e in fs.list_audit(channel="instagram")] == ["b", "a"]
    assert fs.count_audit_since("executed", "instagram", timedelta(hours=1)) == 2


def test_full_approval_flow_on_firestore_store(fs, registry):
    """Executor + queue berjalan di atas FirestoreStore tanpa perubahan."""
    q, ex = ApprovalQueue(fs), Executor(registry, fs)
    done = ex.execute(q.approve(q.propose(prop()).id))
    assert done.status == ActionStatus.EXECUTED
    fs.reset()
    assert fs.list_actions() == []
