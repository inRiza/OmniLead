"""Izin agen: manual, hybrid, dan auto, dengan pagar Guard dan Jeda yang tidak bisa dimatikan."""

import copy

import httpx

from omnilead.agent_client import AgentClient
from omnilead.approvals.executor import Paused
from omnilead.ingest import IngestService
from omnilead.models import ActionStatus, EventIn
from tests.test_ingest_api import CANNED, FakeAgent

PASS = [{"check": "konsistensi_harga", "status": "pass", "note": ""}]


def response(intents=("pertanyaan_umum",), urgency="rendah"):
    r = copy.deepcopy(CANNED)
    r["triage"] = {"intents": list(intents), "urgency": urgency, "entities": {}}
    r["proposals"] = [
        {"kind": "send_message", "channel": "instagram", "recipient": "@ani", "post_ref": "p1", "comment_ref": "c1",
         "text": "Kami antar ke Bandung dan Cimahi ya kak", "guard": PASS},
        {"kind": "send_message", "channel": "instagram", "recipient": "@ani", "post_ref": "p1", "comment_ref": "c1",
         "text": "Paket B total Rp2.100.000", "guard": PASS},
        {"kind": "reply_comment", "channel": "instagram", "post_ref": "p1", "comment_ref": "c1",
         "recipient": "@ani", "text": "Detailnya sudah kami DM ya kak", "public": True, "guard": PASS},
        {"kind": "crm_update", "channel": "instagram", "payload": {"stage": "tertarik"}, "guard": PASS},
        {"kind": "send_message", "channel": "instagram", "recipient": "@ani", "post_ref": "p1", "comment_ref": "c1",
         "text": "Diskon 70% untuk kakak", "guard": [{"check": "kebijakan_diskon", "status": "warn", "note": ""}]},
    ]
    return r


def run(store, queue, executor, mode, **kw):
    settings = store.get_settings()
    settings.autonomy = mode
    store.save_settings(settings)
    agent = FakeAgent()
    agent.response = response(**kw)
    service = IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)), executor)
    service.ingest(EventIn(channel="instagram", kind="comment", external_id=f"m-{mode}",
                           sender={"handle": "@ani", "name": "Ani"}, text="bisa kirim ke Cimahi?",
                           post_ref="p1", comment_ref="c1"))
    return {a.text or a.kind.value: a.status for a in store.list_actions()}


def test_manual_keeps_everything_for_the_owner(store, queue, executor, ig):
    statuses = run(store, queue, executor, "manual")
    assert set(statuses.values()) == {ActionStatus.PENDING} and ig.posted == []


def test_hybrid_runs_only_low_risk_actions(store, queue, executor, ig):
    statuses = run(store, queue, executor, "hybrid")
    assert statuses["Kami antar ke Bandung dan Cimahi ya kak"] == ActionStatus.EXECUTED
    assert statuses["crm_update"] == ActionStatus.EXECUTED
    assert statuses["Paket B total Rp2.100.000"] == ActionStatus.PENDING
    assert statuses["Detailnya sudah kami DM ya kak"] == ActionStatus.PENDING
    assert statuses["Diskon 70% untuk kakak"] == ActionStatus.PENDING
    assert any(e.event == "auto_approved" and e.actor == "agent" for e in store.list_audit())


def test_hybrid_keeps_quotes_and_complaints_for_the_owner(store, queue, executor):
    statuses = run(store, queue, executor, "hybrid", intents=("minta_penawaran",), urgency="tinggi")
    assert statuses["Kami antar ke Bandung dan Cimahi ya kak"] == ActionStatus.PENDING
    assert statuses["crm_update"] == ActionStatus.EXECUTED


def test_auto_runs_everything_that_passes_guard_but_never_guard_warnings(store, queue, executor):
    statuses = run(store, queue, executor, "auto")
    assert statuses["Kami antar ke Bandung dan Cimahi ya kak"] == ActionStatus.EXECUTED
    assert statuses["Detailnya sudah kami DM ya kak"] == ActionStatus.EXECUTED
    # Batas platform tetap berlaku di mode otomatis: private reply hanya sekali per komentar.
    assert statuses["Paket B total Rp2.100.000"] == ActionStatus.FAILED
    assert statuses["Diskon 70% untuk kakak"] == ActionStatus.PENDING


def test_pause_returns_auto_actions_to_the_owner(store, queue, ig):
    class PausingExecutor:
        def execute(self, action):
            raise Paused("Agent dijeda. Semua aksi ditahan.")

    settings = store.get_settings()
    settings.autonomy = "auto"
    store.save_settings(settings)
    agent = FakeAgent()
    agent.response = response()
    service = IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)),
                            PausingExecutor())
    service.ingest(EventIn(channel="instagram", kind="comment", external_id="m-pause",
                           sender={"handle": "@ani", "name": "Ani"}, text="bisa kirim?", post_ref="p1", comment_ref="c1"))
    assert all(a.status == ActionStatus.PENDING and a.decided_at is None for a in store.list_actions())
    assert ig.posted == [] and any(e.event == "auto_held" for e in store.list_audit())


def test_hybrid_keeps_deal_and_batal_for_the_owner():
    from omnilead.autonomy import is_low_risk
    from omnilead.models import Action, ActionKind
    from datetime import datetime, timezone

    def crm(stage):
        return Action(id="a", kind=ActionKind.CRM_UPDATE, channel="whatsapp", payload={"stage": stage},
                      status=ActionStatus.PENDING, created_at=datetime.now(timezone.utc))

    assert is_low_risk(crm("tertarik"), None)
    assert not is_low_risk(crm("deal"), None) and not is_low_risk(crm("batal"), None)
