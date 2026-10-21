"""Ingest + API end-to-end dengan service agen tiruan (httpx MockTransport)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.agent_client import AgentClient
from omnilead.api import deps
from omnilead.ingest import IngestService
from omnilead.main import create_app

CANNED = {
    "event_id": "x",
    "triage": {"intents": ["minta_penawaran"], "urgency": "tinggi",
               "entities": {"company": "PT Maju Jaya", "qty": 60}},
    "score": {"score": 86, "label": "Hot", "reasons": ["korporat"]},
    "crm": {"stage": "penawaran", "summary": "Minta penawaran 60 pax", "score": 86,
            "label": "Hot", "score_reason": "korporat"},
    "proposals": [
        {"kind": "reply_comment", "channel": "instagram", "post_ref": "p1", "comment_ref": "c1",
         "recipient": "@ani", "text": "Sudah kami DM ya kak", "public": True,
         "guard": [{"check": "konsistensi_harga", "status": "pass", "note": ""}]},
        {"kind": "send_message", "channel": "instagram", "post_ref": "p1", "comment_ref": "c1",
         "recipient": "@ani", "text": "Paket B total Rp2.100.000"},
        {"kind": "crm_update", "channel": "instagram", "payload": {"stage": "penawaran"}},
    ],
    "flagged_for_review": False, "review_reason": "",
    "trace": {"goal": "Tanggapi", "plan": ["a"], "steps": [], "guard_summary": "3/3 lolos"},
}


class FakeAgent:
    def __init__(self):
        self.calls: list[dict] = []
        self.down = False
        self.response = CANNED

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            return httpx.Response(503)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "engine": "rule", "can_send": False})
        self.calls.append(json.loads(request.content))
        return httpx.Response(200, json=self.response)


@pytest.fixture
def agent():
    return FakeAgent()


@pytest.fixture
def client(store, registry, queue, executor, agent):
    ac = AgentClient("http://agent", transport=httpx.MockTransport(agent.handler))
    ing = IngestService(store, queue, ac)
    app = create_app()
    o = app.dependency_overrides
    o[deps.get_store] = lambda: store
    o[deps.get_registry] = lambda: registry
    o[deps.get_queue] = lambda: queue
    o[deps.get_executor] = lambda: executor
    o[deps.get_agent_client] = lambda: ac
    o[deps.get_ingest] = lambda: ing
    return TestClient(app)


def ev(**kw):
    base = {"channel": "instagram", "kind": "comment", "external_id": "m1",
            "sender": {"handle": "@Ani.MajuJaya", "name": "Ani"},
            "text": "bisa buat 60 orang tgl 30? harga?", "post_ref": "p1", "comment_ref": "c1"}
    base.update(kw)
    return base


def test_event_creates_lead_and_queues_proposals(client, agent):
    r = client.post("/events", json=ev())
    assert r.status_code == 200 and r.json()["status"] == "analyzed"
    pending = client.get("/actions", params={"status": "pending"}).json()
    assert len(pending) == 3
    assert all(a["event_id"] == r.json()["id"] and a["trace"]["goal"] for a in pending)
    lead = client.get("/leads").json()[0]
    assert lead["score"] == 86 and lead["company"] == "PT Maju Jaya"
    sent = agent.calls[0]
    assert sent["event"]["text"].startswith("bisa buat")
    assert "token" not in json.dumps(sent).lower()


def test_dedup_does_not_call_agent_twice(client, agent):
    a = client.post("/events", json=ev()).json()
    b = client.post("/events", json=ev()).json()
    assert a["id"] == b["id"] and len(agent.calls) == 1
    assert len(client.get("/actions").json()) == 3


def test_exact_phone_and_email_merge_across_channels(client):
    client.post("/events", json=ev(channel="email", kind="email", external_id="g1",
                                   sender={"email": "Ani@MajuJaya.example", "phone": "081234500001"}))
    r = client.post("/events", json=ev(channel="whatsapp", kind="message", external_id="w1",
                                       sender={"phone": "+62 812-3450-0001", "name": "Ani"}))
    leads = client.get("/leads").json()
    assert len(leads) == 1 and r.json()["lead_id"] == leads[0]["id"]
    client.post("/events", json=ev(external_id="i1", sender={"handle": "@ani", "phone": "081234500001"}))
    detail = client.get(f"/leads/{leads[0]['id']}").json()
    assert len(detail["timeline"]) >= 2
    assert "instagram:ani" in detail["lead"]["handles"] and detail["merge_evidence"]


def test_pause_holds_events_and_blocks_approval_then_resumes(client, agent):
    assert client.post("/settings/pause", json={"paused": True}).json()["paused"] is True
    r = client.post("/events", json=ev())
    assert r.json()["status"] == "held" and agent.calls == []
    out = client.post("/settings/pause", json={"paused": False}).json()
    assert out["reprocessed_events"] == 1 and len(agent.calls) == 1
    aid = client.get("/actions", params={"status": "pending"}).json()[0]["id"]
    client.post("/settings/pause", json={"paused": True})
    assert client.post(f"/actions/{aid}/approve", json={}).status_code == 423


def test_agent_down_marks_event_not_crash(client, agent):
    agent.down = True
    r = client.post("/events", json=ev())
    assert r.status_code == 200 and r.json()["status"] == "agent_error"
    assert client.get("/agent/health").json()["reachable"] is False


def test_flagged_event_has_no_actions(client, agent):
    agent.response = {**CANNED, "proposals": [], "flagged_for_review": True,
                      "review_reason": "Pesan ini dicurigai berisi instruksi manipulatif dan perlu ditinjau manual."}
    r = client.post("/events", json=ev(external_id="inj"))
    assert r.json()["status"] == "review"
    assert client.get("/actions").json() == []


def test_approve_flow_and_double_approve_conflict(client, ig):
    client.post("/events", json=ev())
    acts = {a["kind"]: a for a in client.get("/actions").json()}
    pub = acts["reply_comment"]
    ok = client.post(f"/actions/{pub['id']}/approve", json={"edited_text": "Detailnya sudah kami DM ya kak"})
    assert ok.status_code == 200 and ok.json()["status"] == "executed" and ok.json()["edited"]
    assert ig.posted
    assert client.post(f"/actions/{pub['id']}/approve", json={}).status_code == 409
    rej = acts["send_message"]
    assert client.post(f"/actions/{rej['id']}/reject", json={"reason": "terlalu formal"}).status_code == 200
    assert "terlalu formal" in client.get("/settings").json()["preferences"]


def test_channel_switch_blocks_approval_with_409(client):
    client.post("/events", json=ev())
    s = client.patch("/settings/channels/instagram", json={"enabled": False}).json()
    assert "instagram" in s["disabled_channels"]
    pub = next(a for a in client.get("/actions").json() if a["kind"] == "reply_comment")
    assert client.post(f"/actions/{pub['id']}/approve", json={}).status_code == 409


def test_api_key_required_when_configured(client, monkeypatch):
    from omnilead.config import get_settings

    monkeypatch.setenv("OMNILEAD_API_KEY", "rahasia")
    get_settings.cache_clear()
    try:
        assert client.get("/leads").status_code == 401
        assert client.get("/leads", headers={"X-API-Key": "rahasia"}).status_code == 200
        assert client.get("/health").status_code == 200
    finally:
        monkeypatch.delenv("OMNILEAD_API_KEY")
        get_settings.cache_clear()


def test_trivial_followup_does_not_downgrade_hot_lead(client, agent):
    client.post("/events", json=ev())
    low = {**CANNED, "score": {"score": 20, "label": "Cold", "reasons": []},
           "crm": {"stage": "baru", "summary": "halo", "score": 20, "label": "Cold", "score_reason": "x"},
           "proposals": []}
    agent.response = low
    client.post("/events", json=ev(external_id="m2", text="halo?"))
    lead = client.get("/leads").json()[0]
    assert lead["score"] == 86 and lead["label"] == "Hot"


def test_sender_own_name_not_treated_as_other_customer_data(client, store, agent):
    from datetime import datetime, timezone

    from omnilead.models import Lead

    now = datetime.now(timezone.utc)
    store.save_lead(Lead(id="ani-lama", name="Ani", phones=["6281234500001"], created_at=now, updated_at=now))
    store.save_lead(Lead(id="budi", name="Budi", created_at=now, updated_at=now))
    client.post("/events", json=ev(external_id="own1", sender={"handle": "@ani.x", "name": "Ani"}))
    terms = agent.calls[-1]["protected_terms"]
    assert "Ani" not in terms and "6281234500001" in terms and "Budi" in terms
