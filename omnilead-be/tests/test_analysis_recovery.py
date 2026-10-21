"""Recover expired jobs without automatically sending or replaying old tasks."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from omnilead.analysis_state import visible_analysis_state
from omnilead.agent_client import AgentClient, AgentResult
from omnilead.ingest import IngestService
from omnilead.models import Event, EventIn, Sender, Channel
from tests.test_ingest_api import CANNED, agent, client  # noqa: F401


def saved_event(store, status="processing", expiry=None):
    event = Event(id="orphaned-job", channel=Channel.INSTAGRAM, kind="dm", external_id="orphan-1",
        sender=Sender(handle="customer"), text="Jam buka?", status=status,
        trace={"run_id": "old-run", "lease_expires_at": expiry} if expiry else None)
    store.save_event(event)
    return event


@pytest.mark.parametrize("status", ["new", "processing"])
def test_expired_job_is_visible_as_recoverable_error(store, client, status):
    expiry = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    saved_event(store, status, expiry)
    [event] = client.get("/events").json()
    assert event["status"] == "agent_error" and "Proses ulang" in event["review_reason"]


def test_orphaned_legacy_processing_job_can_be_retried(store, client, agent, ig):
    event = saved_event(store)
    response = client.post(f"/events/{event.id}/analyze?background=true")
    assert response.status_code == 200
    assert store.get_event(event.id).status == "analyzed"
    assert len(agent.calls) == 1 and len(store.list_actions()) == 3
    assert ig.posted == []


@pytest.mark.parametrize("status", ["new", "processing"])
def test_active_lease_cannot_be_queued_again(store, client, agent, status):
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
    event = saved_event(store, status, expiry)
    assert client.post(f"/events/{event.id}/analyze?background=true").status_code == 409
    assert agent.calls == []


def test_expired_queued_job_does_not_start_when_background_task_wakes_up(store, queue, agent):
    ac = AgentClient("http://agent", transport=httpx.MockTransport(agent.handler))
    service = IngestService(store, queue, ac)
    event = saved_event(store, "new", (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat())
    final = service.process(event, expected_run_id="old-run")
    assert final.status == "agent_error" and agent.calls == []


def test_superseded_queued_task_does_not_start(store, queue, agent):
    service = IngestService(store, queue, AgentClient("http://agent", transport=httpx.MockTransport(agent.handler)))
    original = service.prepare(saved_event(store))
    old_run = original.trace["run_id"]
    newer = service.prepare(original.model_copy())
    assert newer.trace["run_id"] != old_run
    final = service.process(original, expected_run_id=old_run)
    assert final.trace["run_id"] == newer.trace["run_id"] and agent.calls == []


def test_result_from_superseded_run_cannot_create_actions(store, queue):
    event = saved_event(store, "new")

    class SupersededAgent:
        timeout_seconds = 60

        def analyze_stream(self, payload, on_progress):
            current = store.get_event(event.id)
            current.trace = {"run_id": "newer-run"}
            current.status = "new"
            store.save_event(current)
            return AgentResult.model_validate(CANNED)

    final = IngestService(store, queue, SupersededAgent()).process(event)
    assert final.trace["run_id"] == "newer-run" and store.list_actions() == []
