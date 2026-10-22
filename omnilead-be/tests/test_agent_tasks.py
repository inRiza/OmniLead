"""Task board and clock tests: isolated SQLite + scripted agent, no model/platform calls."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from omnilead.agent_tasks import TaskInput, change_task, create_task, execute_task, run_due_tasks, timing
from omnilead.store import Store

NOW = datetime(2026, 10, 23, 3, 30, tzinfo=timezone.utc)  # 10:30 WIB, Friday


def payload(**kw):
    return TaskInput(title="Cek inbox", instruction="Cek pesan Instagram", channels=["instagram"], **kw)


@pytest.mark.parametrize("schedule,cron,due", [
    ("every_15m", "*/15 * * * *", "2026-10-23T03:45:00+00:00"),
    ("hourly", "0 * * * *", "2026-10-23T04:00:00+00:00"),
    ("daily", "0 9 * * *", "2026-10-24T02:00:00+00:00"),
    ("weekly", "0 9 * * 1", "2026-10-26T02:00:00+00:00"),
])
def test_schedule_uses_wib(schedule, cron, due):
    actual, expression = timing(payload(schedule=schedule).model_dump(mode="json"), NOW)
    assert (actual, expression) == (due, cron)


def test_task_survives_reopen_and_is_workspace_scoped(tmp_path):
    path = tmp_path / "one.db"
    task = create_task(Store(path), payload())
    assert Store(path).get_agent_task(task["id"])["title"] == "Cek inbox"
    assert Store(tmp_path / "two.db").get_agent_task(task["id"]) is None


def test_atomic_claim_cannot_overwrite_new_revision(store):
    task = create_task(store, payload())
    first = {**task, "revision": 1, "status": "running"}
    assert store.save_agent_task(first, 0)
    assert not store.save_agent_task({**first, "result": "duplicate"}, 0)
    assert store.get_agent_task(task["id"])["result"] == ""


def test_pause_resume_complete(store):
    task = create_task(store, payload(schedule="daily"))
    assert change_task(store, task["id"], "pause")["status"] == "paused"
    assert change_task(store, task["id"], "resume")["status"] == "scheduled"
    done = change_task(store, task["id"], "complete")
    assert done["status"] == "done" and done["next_run_at"] is None


def test_blank_and_past_schedule_rejected():
    with pytest.raises(ValidationError):
        TaskInput(title=" ", instruction="x", channels=["instagram"])
    with pytest.raises(ValidationError):
        payload(schedule="once", at=datetime.now(timezone.utc) - timedelta(days=1))


def test_runner_records_real_stream_and_completes(store, monkeypatch):
    task = create_task(store, payload())
    def stream(*a, **kw):
        assert kw["allow_task_changes"] is False
        yield {"type": "thoughts", "text": "Perlu memeriksa pesan."}
        yield {"type": "tool_result", "tool": "baca_pesan_baru", "ok": True}
        yield {"type": "message", "text": "Selesai memeriksa."}
    monkeypatch.setattr("omnilead.chat.run_chat", stream)
    out = execute_task(store, task["id"], None, None)
    assert out["status"] == "done" and out["result"] == "Selesai memeriksa."
    assert out["events"][0]["type"] == "thoughts"
    with pytest.raises(ValueError):
        execute_task(store, task["id"], None, None)


def test_unsupported_channel_blocked_instead_of_fake_success(store):
    task = create_task(store, TaskInput(title="WhatsApp", instruction="Cek chat", channels=["whatsapp"]))
    out = execute_task(store, task["id"], None, None)
    assert out["status"] == "blocked" and "whatsapp" in out["result"]


def test_failed_tool_marks_task_blocked(store, monkeypatch):
    task = create_task(store, payload())
    monkeypatch.setattr("omnilead.chat.run_chat", lambda *a, **k: iter([
        {"type": "tool_result", "tool": "x", "ok": False}, {"type": "message", "text": "Perlu login"}]))
    assert execute_task(store, task["id"], None, None)["status"] == "blocked"


def test_clock_claims_due_occurrence_once(store, monkeypatch):
    task = create_task(store, payload(schedule="once", at=datetime.now(timezone.utc) + timedelta(hours=1)))
    monkeypatch.setattr("omnilead.chat.run_chat", lambda *a, **k: iter([{"type": "tool_result", "tool": "x", "ok": True}, {"type": "message", "text": "Selesai"}]))
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    assert run_due_tasks(store, None, None, future) == [task["id"]]
    assert run_due_tasks(store, None, None, future) == []


def test_clock_respects_global_pause(store):
    task = create_task(store, payload(schedule="hourly"))
    settings = store.get_settings()
    settings.paused = True
    store.save_settings(settings)
    assert run_due_tasks(store, None, None, datetime.now(timezone.utc) + timedelta(days=1)) == []
    assert store.get_agent_task(task["id"])["status"] == "scheduled"
