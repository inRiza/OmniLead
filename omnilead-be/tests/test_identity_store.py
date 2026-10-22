import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from omnilead.agent_client import AgentClient
from omnilead.api.webhooks import _enqueue, _process_jobs, drain_inbox, enrich_sender
from omnilead.approvals.auto import AutoSender
from omnilead.dedup import excluded_pairs, scan_duplicates
from omnilead.identity import canon_email, email_domain, find_candidates, identity_keys
from omnilead.ingest import IngestService, mentioned_contacts
from omnilead.models import ActionKind, ActionStatus, Channel, EventIn, Lead, ProposedAction, Sender
from omnilead.store import Store
from tests.test_ingest_api import CANNED, FakeAgent

NOW = datetime.now(timezone.utc)


def lead(id, name=None, **kw):
    return Lead(id=id, name=name, created_at=kw.pop("created_at", NOW), updated_at=NOW, **kw)


@pytest.fixture
def agent():
    a = FakeAgent()
    a.response = {**CANNED, "proposals": []}
    return a


@pytest.fixture
def ingest(store, queue, executor, agent):
    auto = AutoSender(store, queue, executor)
    return IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)),
                         on_proposed=auto.handle)


def ev(external_id, channel=Channel.WHATSAPP, kind="message", text="halo kak", meta=None, **sender):
    return EventIn(channel=channel, kind=kind, external_id=external_id, sender=Sender(**sender), text=text,
                   meta=meta or {})


def merges(store):
    return store.list_actions(kind=ActionKind.MERGE)


@pytest.mark.parametrize("raw,expected", [
    ("A.N.I+promo@GMAIL.com", "ani@gmail.com"),
    ("ani@googlemail.com", "ani@gmail.com"),
    ("rina+toko@outlook.com", "rina@outlook.com"),
    ("rina+toko@majujaya.co.id", "rina+toko@majujaya.co.id"),
    ("bukan-email", None),
])
def test_canon_email(raw, expected):
    assert canon_email(raw) == expected


def test_email_domain_ignores_free_providers():
    assert email_domain("ani@gmail.com") is None
    assert email_domain("ani@majujaya.co.id") == "majujaya.co.id"


def test_identity_index_finds_by_canonical_email(store):
    store.save_lead(lead("a", "Ani", emails=["a.n.i@gmail.com"], phones=["6281"]))
    assert [x.id for x in store.find_leads_by_identity("email:ani@gmail.com")] == ["a"]
    assert [x.id for x in store.find_leads_by_identity("phone:6281")] == ["a"]
    store.delete_lead("a")
    assert store.find_leads_by_identity("phone:6281") == []


def test_identity_index_backfills_existing_db(tmp_path):
    first = Store(tmp_path / "x.db")
    first.save_lead(lead("a", phones=["6281"]))
    first._db.execute("DELETE FROM lead_identity")
    first._db.commit()
    reopened = Store(tmp_path / "x.db")
    assert [x.id for x in reopened.find_leads_by_identity("phone:6281")] == ["a"]
    assert identity_keys(reopened.get_lead("a")) == {"phone:6281"}


def test_gmail_alias_matches_existing_lead(ingest, store):
    first, _ = ingest.ingest(ev("e1", Channel.EMAIL, "email", email="ani.rahma@gmail.com", name="Ani"))
    second, _ = ingest.ingest(ev("e2", Channel.EMAIL, "email", email="AniRahma+order@gmail.com"))
    assert first.lead_id == second.lead_id
    assert len(store.list_leads()) == 1


def test_conflict_between_two_leads_is_proposed_not_silently_attached(ingest, store):
    a, _ = ingest.ingest(ev("w1", phone="081200000001", name="Ani"))
    b, _ = ingest.ingest(ev("g1", Channel.EMAIL, "email", email="ani@majujaya.co.id", name="Ani Kantor"))
    assert a.lead_id != b.lead_id
    both, _ = ingest.ingest(ev("w2", phone="081200000001", email="ani@majujaya.co.id"))
    assert both.lead_id == a.lead_id
    assert "ani@majujaya.co.id" not in store.get_lead(a.lead_id).emails
    (proposal,) = merges(store)
    assert proposal.payload["source_lead_id"] == b.lead_id and proposal.payload["target_lead_id"] == a.lead_id
    assert proposal.payload["confidence"] == 0.97 and "Email sama" in proposal.payload["evidence"][0]
    assert any(e.event == "merge_strengthened" for e in store.list_audit(limit=50))
    assert any(e.event == "identity_conflict" for e in store.list_audit(limit=50))


def test_contact_mentioned_in_text_proposes_merge(ingest, store):
    owner, _ = ingest.ingest(ev("g1", Channel.EMAIL, "email", email="rina@nusacorp.co.id", name="Rina"))
    dm, _ = ingest.ingest(ev("i1", Channel.INSTAGRAM, "dm", handle="1789", text="kak ini email saya rina@nusacorp.co.id ya"))
    assert dm.lead_id != owner.lead_id
    (proposal,) = merges(store)
    assert proposal.payload["target_lead_id"] == owner.lead_id
    assert proposal.payload["confidence"] == 0.85
    assert store.get_event(dm.id).meta["mentioned_contacts"] == ["rina@nusacorp.co.id"]


def test_mentioned_contacts_parses_email_and_phone():
    found = {k for _, _, k in mentioned_contacts("WA saya 0812-3456-7890 atau ani@gmail.com, 021 5555")}
    assert found == {"phone:6281234567890", "email:ani@gmail.com"}


def test_auto_merge_above_threshold_when_auto_send(ingest, store):
    s = store.get_settings()
    s.autonomy = "auto"
    s.auto_merge_threshold = 0.9
    store.save_settings(s)
    a, _ = ingest.ingest(ev("w1", phone="081200000001", name="Ani"))
    b, _ = ingest.ingest(ev("g1", Channel.EMAIL, "email", email="ani@majujaya.co.id", name="Ani Kantor"))
    ingest.ingest(ev("w2", phone="081200000001", email="ani@majujaya.co.id"))
    (proposal,) = merges(store)
    assert proposal.status == ActionStatus.EXECUTED
    assert store.get_lead(b.lead_id) is None
    merged = store.get_lead(a.lead_id)
    assert "ani@majujaya.co.id" in merged.emails
    assert merged.identity_sources["email:ani@majujaya.co.id"]["source"] == "merge"
    audit = next(e for e in store.list_audit(limit=50) if e.event == "identity_merged" and e.action_id == proposal.id)
    assert audit.actor == "agent" and "otomatis" in audit.detail


def test_rejected_pair_is_not_proposed_again(store, queue):
    store.save_lead(lead("old", "Maya Sari", created_at=NOW - timedelta(days=3)))
    store.save_lead(lead("new", "Maya Sari"))
    (first,) = scan_duplicates(store, queue)
    assert first.payload["source_lead_id"] == "new" and first.payload["target_lead_id"] == "old"
    queue.reject(first.id, "Bukan orang yang sama")
    assert frozenset(("old", "new")) in excluded_pairs(store)
    assert scan_duplicates(store, queue) == []


def test_bad_feedback_on_merge_also_excludes_pair(store, queue):
    store.save_lead(lead("old", "Maya Sari", created_at=NOW - timedelta(days=3)))
    store.save_lead(lead("new", "Maya Sari"))
    (first,) = scan_duplicates(store, queue)
    queue.feedback(first.id, "bad", "beda orang")
    assert scan_duplicates(store, queue) == []


def test_fuzzy_names_honorifics_and_office_domain():
    new = lead("n", "Kak Rinna", emails=["rinna@nusacorp.co.id"])
    old = lead("o", "Rina Wulandari", emails=["rina@nusacorp.co.id"])
    (cand,) = find_candidates(new, [old])
    assert cand.lead.id == "o"
    assert any("mirip" in e for e in cand.evidence) and any("Domain email kantor" in e for e in cand.evidence)


def test_honorific_alone_is_not_a_name_match():
    assert find_candidates(lead("n", "Kak Budi"), [lead("o", "Kak Sari")]) == []


def test_identity_added_to_existing_lead_triggers_fuzzy_scan(ingest, store):
    store.save_lead(lead("maya", "Maya Lestari", created_at=NOW - timedelta(days=5)))
    first, _ = ingest.ingest(ev("w1", phone="081300000001", name="Pelanggan Baru"))
    assert merges(store) == []
    s = store.get_lead(first.lead_id)
    s.name = "Maya Lestari"
    store.save_lead(s)
    ingest.ingest(ev("w2", phone="081300000001", email="maya.l@gmail.com"))
    assert [m.payload["target_lead_id"] for m in merges(store)] == ["maya"]


def test_manual_merge_and_find_duplicates_routes(tmp_path):
    from fastapi.testclient import TestClient

    from omnilead.api.deps import get_store
    from omnilead.main import app

    st = Store(tmp_path / "api.db")
    st.save_lead(lead("a", "Sari", phones=["6281"], created_at=NOW - timedelta(days=1)))
    st.save_lead(lead("b", "Sari Indah", emails=["sari@x.id"], identity_sources={"email:sari@x.id": {"channel": "email"}}))
    st.save_lead(lead("c", "Joko Susilo"))
    st.save_lead(lead("d", "Joko Susilo"))
    app.dependency_overrides[get_store] = lambda: st
    try:
        client = TestClient(app)
        r = client.post("/leads/a/merge", json={"source_lead_id": "b"})
        assert r.status_code == 200 and r.json()["status"] == "executed" and r.json()["channel"] == "email"
        assert st.get_lead("b") is None and "sari@x.id" in st.get_lead("a").emails
        assert client.get("/leads/a").json()["undoable_merges"][0]["action_id"] == r.json()["id"]
        assert client.post("/leads/a/merge", json={"source_lead_id": "a"}).status_code == 409
        assert client.post("/leads/a/merge", json={"source_lead_id": "zzz"}).status_code == 404
        found = client.post("/leads/find-duplicates").json()
        assert found["proposed"] == 1 and found["merged"] == 0
    finally:
        app.dependency_overrides.clear()


def test_actions_filters_and_audit_cursor(store, queue):
    a = queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT, post_ref="p",
                                     comment_ref="c", text="x", lead_id="L1"))
    queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.FOLLOWUP, text="y", lead_id="L2"))
    assert [x.id for x in store.list_actions(lead_id="L1")] == [a.id]
    assert [x.kind for x in store.list_actions(kind=ActionKind.FOLLOWUP)] == [ActionKind.FOLLOWUP]
    assert len(store.list_actions(ActionStatus.PENDING, limit=1)) == 1
    for i in range(5):
        store.audit("executed", f"d{i}", channel="instagram", lead_id="L1")
    page1 = store.list_audit(limit=3, lead_id="L1", event="executed")
    page2 = store.list_audit(limit=3, lead_id="L1", event="executed", before_id=page1[-1].id)
    assert [e.detail for e in page1] == ["d4", "d3", "d2"] and [e.detail for e in page2] == ["d1", "d0"]
    assert all(e.event == "executed" for e in store.list_audit(event="executed"))


def test_events_cursor(store):
    from omnilead.models import Event

    for i in range(4):
        store.save_event(Event(id=f"e{i}", channel=Channel.WHATSAPP, kind="message", external_id=f"x{i}",
                               sender=Sender(), text="t", ts=NOW - timedelta(minutes=i), lead_id="L"))
    first = store.list_events(limit=2)
    rest = store.list_events(limit=10, before=first[-1].ts)
    assert [e.id for e in first] == ["e0", "e1"] and [e.id for e in rest] == ["e2", "e3"]


def test_existing_actions_db_gets_lead_and_kind_columns(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE actions (id TEXT PRIMARY KEY, data TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)")
    data = {"id": "a1", "channel": "instagram", "kind": "followup", "text": "x", "status": "pending",
            "created_at": NOW.isoformat(), "lead_id": "L9"}
    db.execute("INSERT INTO actions VALUES (?, ?, ?, ?)", ("a1", json.dumps(data), "pending", NOW.isoformat()))
    db.commit()
    db.close()
    st = Store(path)
    assert [a.id for a in st.list_actions(lead_id="L9", kind=ActionKind.FOLLOWUP)] == ["a1"]


def test_webhook_jobs_are_durable_and_drained(ingest, store, monkeypatch):
    events = [ev("w1", phone="0811", text="satu"), ev("w2", phone="0812", text="dua")]
    ids = _enqueue(ingest, events)
    assert [store.get_job(i)["status"] for i in ids] == ["pending", "pending"]
    calls = {"n": 0}
    real = ingest.ingest

    def flaky(e, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("instance mati")
        return real(e, **kw)

    monkeypatch.setattr(ingest, "ingest", flaky)
    _process_jobs(ingest, ids)
    assert store.get_job(ids[0])["status"] == "failed" and store.get_job(ids[1])["status"] == "done"
    assert drain_inbox(ingest) == 0
    store._db.execute("UPDATE jobs SET updated_at = ?", ((NOW - timedelta(minutes=10)).isoformat(),))
    store._db.commit()
    assert drain_inbox(ingest) == 1
    assert store.get_job(ids[0])["status"] == "done"
    assert len(store.list_events()) == 2
    assert _enqueue(ingest, events[:1]) == ["whatsapp:w1"] and store.get_job("whatsapp:w1")["status"] == "done"


def test_enrich_instagram_dm_keeps_igsid_and_adds_username(ingest, store):
    class Conn:
        def user_profile(self, user_id):
            assert user_id == "17841"
            return {"name": "Ani Rahma", "username": "ani.rahma"}

    class Reg:
        def get(self, channel):
            return Conn()

    raw = ev("m1", Channel.INSTAGRAM, "dm", handle="17841")
    enriched = enrich_sender(Reg(), raw)
    assert enriched.sender.handle == "17841" and enriched.sender.name == "Ani Rahma"
    assert enriched.meta == {"platform_user_id": "17841", "username": "ani.rahma"}
    comment, _ = ingest.ingest(ev("c1", Channel.INSTAGRAM, "comment", handle="ani.rahma", name="Ani Rahma"))
    dm, _ = ingest.ingest(enriched)
    assert comment.lead_id == dm.lead_id
    assert set(store.get_lead(dm.lead_id).handles) == {"instagram:ani.rahma", "instagram:17841"}


def test_enrich_ignores_failures_and_non_numeric():
    class Reg:
        def get(self, channel):
            raise RuntimeError("down")

    raw = ev("m1", Channel.INSTAGRAM, "dm", handle="17841")
    assert enrich_sender(Reg(), raw) == raw
    named = ev("m2", Channel.INSTAGRAM, "comment", handle="ani")
    assert enrich_sender(Reg(), named) == named
