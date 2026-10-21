"""Webhook, identitas ambigu, jendela kanal, scheduler, dan tempel pesan."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.agent_client import AgentClient
from omnilead.api import deps
from omnilead.config import Settings, get_settings
from omnilead.ingest import IngestService
from omnilead.main import create_app
from omnilead.models import (
    ActionKind, ActionStatus, Channel, Event, Lead, ProposedAction, Sender,
)
from omnilead.windows import check_window
from tests.conftest import FakeConnector, FakeRegistry
from tests.test_ingest_api import CANNED, FakeAgent

SECRET = "app-secret"
NOW = datetime.now(timezone.utc)


def sign(body: bytes, secret: str = SECRET) -> dict:
    return {"x-hub-signature-256": "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}


@pytest.fixture
def wa():
    return FakeConnector(Channel.WHATSAPP, can_write=True)


@pytest.fixture
def agent():
    return FakeAgent()


@pytest.fixture
def client(store, queue, ig, wa, li_handoff, agent):
    from omnilead.approvals.executor import Executor

    registry = FakeRegistry({Channel.INSTAGRAM: ig, Channel.LINKEDIN: li_handoff, Channel.WHATSAPP: wa})
    executor = Executor(registry, store)
    ac = AgentClient("http://agent", transport=httpx.MockTransport(agent.handler))
    ing = IngestService(store, queue, ac)
    settings = Settings(_env_file=None, meta_app_secret=SECRET, meta_verify_token="vt",
                        scheduler_token="sched", gmail_push_token="gp")
    app = create_app()
    o = app.dependency_overrides
    o[deps.get_store] = lambda: store
    o[deps.get_registry] = lambda: registry
    o[deps.get_queue] = lambda: queue
    o[deps.get_executor] = lambda: executor
    o[deps.get_agent_client] = lambda: ac
    o[deps.get_ingest] = lambda: ing
    o[get_settings] = lambda: settings
    return TestClient(app)


def lead(store, id, name, company=None, phones=(), emails=(), handles=()):
    l = Lead(id=id, name=name, company=company, phones=list(phones), emails=list(emails),
             handles=list(handles), created_at=NOW, updated_at=NOW)
    store.save_lead(l)
    return l


def inbound(store, lead_id, channel, ago: timedelta, kind="message", **kw):
    e = Event(id=f"e-{channel.value}-{int(ago.total_seconds())}-{kw.get('comment_ref', '')}",
              channel=channel, kind=kind, external_id=f"x-{channel.value}-{ago}-{kw.get('comment_ref', '')}",
              sender=Sender(handle="h"), text="hai", ts=NOW - ago, lead_id=lead_id, status="analyzed", **kw)
    store.save_event(e)
    return e


# --- webhook ---


def test_meta_verification(client):
    ok = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "1234"})
    assert ok.status_code == 200 and ok.text == "1234"
    bad = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"})
    assert bad.status_code == 403


WA_PAYLOAD = {"entry": [{"changes": [{"value": {
    "contacts": [{"wa_id": "6281234500001", "profile": {"name": "Ani"}}],
    "messages": [{"id": "wamid.A", "from": "6281234500001", "type": "text",
                  "timestamp": str(int(NOW.timestamp())), "text": {"body": "Nunggu penawaran ya kak"}}],
}}]}]}


def test_whatsapp_webhook_signature_and_dedup(client, store, agent):
    body = json.dumps(WA_PAYLOAD).encode()
    assert client.post("/webhooks/whatsapp", content=body).status_code == 403
    assert client.post("/webhooks/whatsapp", content=body, headers=sign(body, "salah")).status_code == 403
    assert store.list_events() == []

    for _ in range(2):  # Meta mengulang kiriman
        r = client.post("/webhooks/whatsapp", content=body, headers=sign(body))
        assert r.status_code == 200 and r.json()["accepted"] == 1
    events = store.list_events()
    assert len(events) == 1 and events[0].channel == Channel.WHATSAPP and events[0].sender.name == "Ani"
    assert len(agent.calls) == 1


def test_instagram_webhook_comment_and_dm(client, store):
    payload = {"entry": [{"time": int(NOW.timestamp()), "changes": [{"field": "comments", "value": {
        "id": "c-9", "text": "harga?", "from": {"id": "1", "username": "ani.majujaya"}, "media": {"id": "post-1"}}}],
        "messaging": [
            {"sender": {"id": "555"}, "timestamp": int(NOW.timestamp() * 1000),
             "message": {"mid": "m-1", "text": "halo kak"}},
            {"sender": {"id": "1"}, "message": {"mid": "m-echo", "text": "balasan kita", "is_echo": True}},
        ]}]}
    body = json.dumps(payload).encode()
    assert client.post("/webhooks/instagram", content=body, headers=sign(body)).json()["accepted"] == 2
    kinds = {e.kind for e in store.list_events()}
    assert kinds == {"comment", "dm"}
    comment = next(e for e in store.list_events() if e.kind == "comment")
    assert comment.comment_ref == "c-9" and comment.post_ref == "post-1" and comment.sender.handle == "ani.majujaya"


def test_gmail_push_needs_token(client):
    body = {"message": {"data": "e30="}}
    assert client.post("/webhooks/gmail", json=body).status_code == 403
    assert client.post("/webhooks/gmail", params={"token": "gp"}, json=body).status_code == 200


# --- identitas ambigu -> usulan merge ---


def merge_actions(store):
    return [a for a in store.list_actions() if a.kind == ActionKind.MERGE]


def test_ambiguous_identity_proposes_merge_and_executes_on_approval(client, store):
    lead(store, "ani", "Ani", "PT Maju Jaya", phones=["6281234500001"])
    r = client.post("/events", json={"channel": "instagram", "kind": "comment", "external_id": "i1",
                                     "sender": {"handle": "@ani.majujaya", "name": "Ani"},
                                     "text": "bisa buat 60 orang?", "post_ref": "p", "comment_ref": "c1"})
    new_id = r.json()["lead_id"]
    assert new_id != "ani" and len(store.list_leads()) == 2  # tidak digabung diam-diam
    (m,) = merge_actions(store)
    assert m.status == ActionStatus.PENDING and m.payload["target_lead_id"] == "ani"
    assert m.payload["confidence"] >= 0.75 and any("Perusahaan sama" in e for e in m.payload["evidence"])

    done = client.post(f"/actions/{m.id}/approve", json={}).json()
    assert done["status"] == "executed"
    assert [l.id for l in store.list_leads()] == ["ani"]
    merged = store.get_lead("ani")
    assert "instagram:ani.majujaya" in merged.handles and "6281234500001" in merged.phones
    assert all(e.lead_id == "ani" for e in store.list_events())
    assert any(a.event == "identity_merged" and a.actor == "owner" for a in store.list_audit())


def test_two_people_named_ani_low_confidence_with_evidence(client, store, agent):
    lead(store, "ani-lain", "Ani", "CV Berkah Sentosa")
    client.post("/events", json={"channel": "instagram", "kind": "comment", "external_id": "i2",
                                 "sender": {"handle": "@ani_x", "name": "Ani"}, "text": "harga?",
                                 "post_ref": "p", "comment_ref": "c2"})
    (m,) = merge_actions(store)
    assert m.payload["confidence"] < 0.5
    assert any("Perusahaan berbeda" in e for e in m.payload["evidence"])


def test_reject_merge_keeps_profiles_separate(client, store):
    lead(store, "ani", "Ani", "PT Maju Jaya")
    client.post("/events", json={"channel": "instagram", "kind": "comment", "external_id": "i3",
                                 "sender": {"handle": "@ani", "name": "Ani"}, "text": "harga?",
                                 "post_ref": "p", "comment_ref": "c3"})
    (m,) = merge_actions(store)
    client.post(f"/actions/{m.id}/reject", json={"reason": "orang berbeda"})
    assert len(store.list_leads()) == 2


# --- jendela kanal ---


def send(queue, channel, lead_id, **kw):
    return queue.propose(ProposedAction(channel=channel, kind=ActionKind.SEND_MESSAGE, text="halo",
                                        recipient="6281234500001", lead_id=lead_id, **kw))


def test_whatsapp_window_open_vs_closed(client, store, queue, wa):
    lead(store, "l1", "Ani")
    inbound(store, "l1", Channel.WHATSAPP, timedelta(hours=2))
    ok = client.post(f"/actions/{send(queue, Channel.WHATSAPP, 'l1').id}/approve", json={}).json()
    assert ok["status"] == "executed" and wa.posted

    lead(store, "l2", "Budi")
    inbound(store, "l2", Channel.WHATSAPP, timedelta(hours=30))
    wa.posted.clear()
    late = client.post(f"/actions/{send(queue, Channel.WHATSAPP, 'l2').id}/approve", json={}).json()
    assert late["status"] == "failed" and "Butuh template resmi" in late["error"] and wa.posted == []


def test_whatsapp_without_any_inbound_blocked(client, store, queue):
    lead(store, "l3", "Cici")
    r = client.post(f"/actions/{send(queue, Channel.WHATSAPP, 'l3').id}/approve", json={}).json()
    assert r["status"] == "failed" and "template" in r["error"].lower()


def test_instagram_private_reply_7_days_and_once(client, store, queue, ig):
    lead(store, "l4", "Dewi")
    inbound(store, "l4", Channel.INSTAGRAM, timedelta(days=2), kind="comment", comment_ref="c-fresh")
    inbound(store, "l4", Channel.INSTAGRAM, timedelta(days=9), kind="comment", comment_ref="c-old")

    first = client.post(f"/actions/{send(queue, Channel.INSTAGRAM, 'l4', comment_ref='c-fresh').id}/approve", json={}).json()
    assert first["status"] == "executed"
    again = client.post(f"/actions/{send(queue, Channel.INSTAGRAM, 'l4', comment_ref='c-fresh').id}/approve", json={}).json()
    assert again["status"] == "failed" and "satu kali" in again["error"]
    old = client.post(f"/actions/{send(queue, Channel.INSTAGRAM, 'l4', comment_ref='c-old').id}/approve", json={}).json()
    assert old["status"] == "failed" and "7 hari" in old["error"]


def test_email_has_no_window(store, queue):
    lead_ = lead(store, "l5", "Eko")
    a = queue.propose(ProposedAction(channel=Channel.EMAIL, kind=ActionKind.SEND_MESSAGE, text="x",
                                     recipient="e@x.co", lead_id=lead_.id))
    assert check_window(store, a).open


# --- scheduler ---


def followup(queue, store, lead_id, due: datetime):
    a = queue.propose(ProposedAction(channel=Channel.WHATSAPP, kind=ActionKind.FOLLOWUP, text="Halo, soal penawaran?",
                                     recipient="6281234500001", lead_id=lead_id, due_at=due))
    queue.approve(a.id)
    stored = store.get_action(a.id)
    stored.status = ActionStatus.EXECUTED
    stored.result_ref = "scheduled"
    store.save_action(stored)
    return stored


def test_scheduler_requires_token(client):
    assert client.post("/scheduler/followups").status_code == 403
    assert client.post("/scheduler/followups", headers={"authorization": "Bearer salah"}).status_code == 403
    assert client.post("/scheduler/followups", headers={"authorization": "Bearer sched"}).status_code == 200


def test_due_followup_becomes_pending_proposal_once(client, store, queue):
    lead(store, "l6", "Fajar")
    f = followup(queue, store, "l6", NOW - timedelta(hours=1))
    hdr = {"authorization": "Bearer sched"}
    out = client.post("/scheduler/followups", headers=hdr).json()
    assert len(out["created"]) == 1
    new = store.get_action(out["created"][0])
    assert new.status == ActionStatus.PENDING and new.kind == ActionKind.SEND_MESSAGE and new.text == f.text
    assert client.post("/scheduler/followups", headers=hdr).json() == {"created": [], "skipped": []}


def test_followup_skipped_when_customer_replied(client, store, queue):
    lead(store, "l7", "Gita")
    f = followup(queue, store, "l7", NOW - timedelta(hours=1))
    reply = inbound(store, "l7", Channel.WHATSAPP, timedelta(minutes=5))
    reply.ts = f.created_at + timedelta(seconds=1)  # pelanggan membalas setelah pengingat dibuat
    store.save_event(reply)
    out = client.post("/scheduler/followups", headers={"authorization": "Bearer sched"}).json()
    assert out["created"] == [] and len(out["skipped"]) == 1


def test_future_followup_not_fired(client, store, queue):
    lead(store, "l8", "Hana")
    followup(queue, store, "l8", NOW + timedelta(days=2))
    assert client.post("/scheduler/followups", headers={"authorization": "Bearer sched"}).json()["created"] == []


def test_daily_summary_prioritises_failures_and_hot_leads(client, store, queue):
    l = lead(store, "l9", "Indra")
    l.label, l.score = "Hot", 90
    store.save_lead(l)
    queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT,
                                 post_ref="p", comment_ref="c", text="x", lead_id="l9"))
    failed = queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT,
                                          post_ref="p", comment_ref="c", text="y", lead_id="l9"))
    f = store.get_action(failed.id)
    f.status, f.error = ActionStatus.FAILED, "token"
    store.save_action(f)
    items = client.get("/summary/today").json()
    assert items[0]["kind"] == "failed" and any(i["kind"] == "hot_waiting" for i in items)


# --- tempel pesan (kanal tanpa API) ---


def test_paste_tiktok_message_then_manual_handoff(client, store, agent):
    agent.response = {**CANNED, "proposals": [
        {"kind": "send_message", "channel": "tiktok", "recipient": "@sari", "text": "Bisa kak, kami kirim ke Bandung."}]}
    r = client.post("/events/paste", json={"channel": "tiktok", "handle": "@sari", "name": "Sari",
                                           "text": "kak bisa kirim hampers ke Bandung?"})
    assert r.status_code == 200 and r.json()["channel"] == "tiktok" and r.json()["status"] == "analyzed"
    (tik,) = [a for a in client.get("/actions").json() if a["channel"] == "tiktok"]
    # kanal tiktok tidak punya API: disetujui -> menunggu dikirim manual, tidak dikirim otomatis
    done = client.post(f"/actions/{tik['id']}/approve", json={}).json()
    assert done["status"] == "awaiting_manual_send"
    assert client.post(f"/actions/{tik['id']}/sent", json={}).json()["status"] == "sent_manually"


def test_paste_image_extracts_via_agent(client, agent, monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v1/extract":
            return httpx.Response(200, json={"handle": "@rina_tt", "name": "Rina", "text": "ready size M kak?"})
        return agent.handler(req)

    ac = AgentClient("http://agent", transport=httpx.MockTransport(handler))
    client.app.dependency_overrides[deps.get_agent_client] = lambda: ac
    r = client.post("/events/paste-image", json={"channel": "tiktok", "image_base64": "aGk=", "mime_type": "image/png"})
    assert r.status_code == 200 and r.json()["text"] == "ready size M kak?" and r.json()["sender"]["handle"] == "@rina_tt"
