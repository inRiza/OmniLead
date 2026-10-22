from datetime import datetime, timedelta, timezone

import pytest

from omnilead.api.webhooks import apply_delivery_statuses, parse_whatsapp_statuses
from omnilead.approvals.auto import AutoSender
from omnilead.approvals.dispatch import dispatch
from omnilead.approvals.executor import RateLimited
from omnilead.connectors.base import ConnectorError, TransientError
from omnilead.models import ActionKind, ActionStatus, Channel, GuardNote, ProposedAction


def proposal(**kw):
    base = dict(channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT, post_ref="p1",
                comment_ref="c1", text="halo kak")
    base.update(kw)
    return ProposedAction(**base)


def enable_auto(store, **kw):
    s = store.get_settings()
    s.auto_send = True
    for k, v in kw.items():
        setattr(s, k, v)
    store.save_settings(s)


@pytest.fixture
def auto(store, queue, executor):
    return AutoSender(store, queue, executor)


def test_auto_send_off_keeps_pending(auto, queue, ig):
    a = auto.handle(queue.propose(proposal()))
    assert a.status == ActionStatus.PENDING
    assert ig.posted == []


def test_auto_send_executes_when_guards_pass(auto, queue, store, ig):
    enable_auto(store)
    a = auto.handle(queue.propose(proposal(guard=[GuardNote(check="harga", status="pass")])))
    assert a.status == ActionStatus.EXECUTED
    assert ig.posted == [("c1", "halo kak")]
    events = [e.event for e in store.list_audit(limit=10)]
    assert "auto_approved" in events and "executed" in events


@pytest.mark.parametrize("status", ["warn", "block"])
def test_auto_send_holds_on_guard_issue(auto, queue, store, ig, status):
    enable_auto(store)
    a = auto.handle(queue.propose(proposal(guard=[GuardNote(check="harga", status=status, note="cek")])))
    assert a.status == ActionStatus.PENDING
    assert a.payload["_auto_held"] is True
    assert ig.posted == []
    again = auto.handle(store.get_action(a.id))
    assert again.status == ActionStatus.PENDING
    assert [e.event for e in store.list_audit(limit=20)].count("auto_send_held") == 1


def test_auto_send_never_merges(auto, queue, store):
    enable_auto(store)
    a = auto.handle(queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind=ActionKind.MERGE,
                                                 payload={"source_lead_id": "a", "target_lead_id": "b"})))
    assert a.status == ActionStatus.PENDING


def test_auto_send_respects_rate_limit_and_dispatch_resumes(auto, queue, store, executor, ig):
    enable_auto(store, rate_limit_per_hour=1)
    auto.handle(queue.propose(proposal(text="satu")))
    b = auto.handle(queue.propose(proposal(text="dua")))
    assert b.status == ActionStatus.APPROVED
    s = store.get_settings()
    s.rate_limit_per_hour = 5
    store.save_settings(s)
    result = dispatch(store, executor, auto)
    assert b.id in result["executed"]
    assert store.get_action(b.id).status == ActionStatus.EXECUTED


def test_dry_run_counts_toward_rate_limit(queue, executor, store):
    s = store.get_settings()
    s.dry_run = True
    s.rate_limit_per_hour = 1
    store.save_settings(s)
    executor.execute(queue.approve(queue.propose(proposal()).id))
    with pytest.raises(RateLimited):
        executor.execute(queue.approve(queue.propose(proposal(text="lagi")).id))


def test_transient_failure_schedules_retry_and_dispatch_retries(queue, executor, store, ig, monkeypatch):
    calls = {"n": 0}

    def flaky(comment_ref, text):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransientError("timeout")
        return "reply-ok"

    monkeypatch.setattr(ig, "reply_comment", flaky)
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    assert a.status == ActionStatus.FAILED and a.attempts == 1 and a.next_retry_at is not None

    assert dispatch(store, executor)["retried"] == []
    later = datetime.now(timezone.utc) + timedelta(minutes=2)
    result = dispatch(store, executor, now=later)
    assert a.id in result["retried"] and a.id in result["executed"]
    done = store.get_action(a.id)
    assert done.status == ActionStatus.EXECUTED and done.attempts == 2 and done.result_ref == "reply-ok"


def test_permanent_failure_has_no_auto_retry(queue, executor, ig, monkeypatch):
    def broken(comment_ref, text):
        raise ConnectorError("ditolak platform")

    monkeypatch.setattr(ig, "reply_comment", broken)
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    assert a.status == ActionStatus.FAILED and a.next_retry_at is None


def test_unexpected_error_does_not_leave_executing(queue, executor, ig, monkeypatch):
    def crash(comment_ref, text):
        raise RuntimeError("boom")

    monkeypatch.setattr(ig, "reply_comment", crash)
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    assert a.status == ActionStatus.FAILED
    assert "boom" in (a.error or "")


def test_retry_stops_after_backoff_exhausted(queue, executor, store, ig, monkeypatch):
    def always(comment_ref, text):
        raise TransientError("down")

    monkeypatch.setattr(ig, "reply_comment", always)
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    now = datetime.now(timezone.utc)
    for step in range(5):
        now += timedelta(hours=1)
        dispatch(store, executor, now=now)
    final = store.get_action(a.id)
    assert final.status == ActionStatus.FAILED
    assert final.attempts == 4 and final.next_retry_at is None


def test_dispatch_recovers_stuck_executing(queue, store, executor):
    a = queue.approve(queue.propose(proposal()).id)
    a.status = ActionStatus.EXECUTING
    a.last_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    store.save_action(a)
    result = dispatch(store, executor)
    assert result["recovered"] == [a.id]
    stuck = store.get_action(a.id)
    assert stuck.status == ActionStatus.FAILED and stuck.next_retry_at is None


def test_dispatch_leaves_recent_executing(queue, store, executor):
    a = queue.approve(queue.propose(proposal()).id)
    a.status = ActionStatus.EXECUTING
    a.last_attempt_at = datetime.now(timezone.utc)
    store.save_action(a)
    assert dispatch(store, executor)["recovered"] == []


def test_dispatch_skips_when_paused(queue, store, executor):
    s = store.get_settings()
    s.paused = True
    store.save_settings(s)
    assert dispatch(store, executor)["skipped"]


def test_feedback_on_executed_and_pending(queue, executor, store):
    done = executor.execute(queue.approve(queue.propose(proposal()).id))
    rated = queue.feedback(done.id, "bad", "Terlalu kaku")
    assert rated.status == ActionStatus.EXECUTED
    assert rated.feedback[-1]["rating"] == "bad"
    assert "Terlalu kaku" in store.get_settings().preferences

    pending = queue.propose(proposal(text="draf"))
    rejected = queue.feedback(pending.id, "bad", "Jangan sebut harga")
    assert rejected.status == ActionStatus.REJECTED

    good = queue.feedback(done.id, "good", "")
    assert good.feedback[-1]["rating"] == "good"


def test_whatsapp_delivery_statuses(queue, store):
    from omnilead.approvals.executor import Executor
    from tests.conftest import FakeConnector, FakeRegistry

    wa = FakeConnector(Channel.WHATSAPP, can_write=True)
    executor = Executor(FakeRegistry({Channel.WHATSAPP: wa}), store)
    a = executor.execute(queue.approve(queue.propose(ProposedAction(
        channel=Channel.WHATSAPP, kind=ActionKind.SEND_MESSAGE, text="halo", recipient="6281")).id))
    assert a.delivery_status == "sent"

    def payload(status, errors=None):
        st = {"id": "msg-id-1", "status": status, "timestamp": "1700000000"}
        if errors:
            st["errors"] = errors
        return {"entry": [{"changes": [{"value": {"statuses": [st]}}]}]}

    assert apply_delivery_statuses(store, parse_whatsapp_statuses(payload("read"))) == 1
    assert store.get_action(a.id).delivery_status == "read"
    assert apply_delivery_statuses(store, parse_whatsapp_statuses(payload("delivered"))) == 0
    assert store.get_action(a.id).delivery_status == "read"
    apply_delivery_statuses(store, parse_whatsapp_statuses(payload("failed", [{"title": "Nomor tidak aktif"}])))
    failed = store.get_action(a.id)
    assert failed.delivery_status == "failed" and failed.error == "Nomor tidak aktif"


def test_feedback_route_and_settings_patch(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from omnilead.api.deps import get_store
    from omnilead.main import app
    from omnilead.store import Store

    st = Store(tmp_path / "api.db")
    app.dependency_overrides[get_store] = lambda: st
    try:
        client = TestClient(app)
        r = client.patch("/settings", json={"auto_send": True, "auto_merge_threshold": 0.8})
        assert r.status_code == 200 and r.json()["auto_send"] is True and r.json()["auto_merge_threshold"] == 0.8
        action = client.post("/actions/propose", json={"channel": "instagram", "kind": "reply_comment",
                                                       "post_ref": "p", "comment_ref": "c", "text": "hai"}).json()
        assert client.post(f"/actions/{action['id']}/feedback", json={"rating": "bad"}).status_code == 422
        r = client.post(f"/actions/{action['id']}/feedback", json={"rating": "bad", "reason": "kurang ramah"})
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        assert client.post("/actions/nope/feedback", json={"rating": "good"}).status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_ingest_auto_sends_passing_proposals(store, queue, executor, ig):
    import httpx

    from omnilead.agent_client import AgentClient
    from omnilead.ingest import IngestService
    from omnilead.models import EventIn, Sender
    from tests.test_ingest_api import CANNED, FakeAgent

    enable_auto(store)
    agent = FakeAgent()
    agent.response = {**CANNED, "proposals": [
        CANNED["proposals"][0],
        {**CANNED["proposals"][1], "guard": [{"check": "konsistensi_harga", "status": "warn", "note": "cek harga"}]},
        CANNED["proposals"][2],
    ]}
    sender = AutoSender(store, queue, executor)
    ingest = IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)),
                           on_proposed=sender.handle)
    event, _ = ingest.ingest(EventIn(channel=Channel.INSTAGRAM, kind="comment", external_id="m1",
                                     sender=Sender(handle="@ani", name="Ani"), text="harga 60 pax?",
                                     post_ref="p1", comment_ref="c1"))
    by_kind = {a.kind: a for a in store.list_actions() if a.event_id == event.id}
    assert by_kind[ActionKind.REPLY_COMMENT].status == ActionStatus.EXECUTED
    assert by_kind[ActionKind.SEND_MESSAGE].status == ActionStatus.PENDING
    assert by_kind[ActionKind.CRM_UPDATE].status == ActionStatus.EXECUTED
    assert store.get_lead(event.lead_id).stage == "penawaran"
