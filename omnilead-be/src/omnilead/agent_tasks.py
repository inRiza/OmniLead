"""Persistent owner tasks and schedules. No direct platform send path.

The local worker and authenticated Cloud Scheduler share an optimistic claim so
one occurrence is never started twice. Failed/interrupted runs require review.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

UTC = timezone.utc
WIB = timezone(timedelta(hours=7))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=1, max_length=1000)
    channels: list[Literal["instagram", "whatsapp", "facebook", "email"]] = Field(min_length=1, max_length=4)
    schedule: Literal["manual", "once", "every_15m", "hourly", "daily", "weekly"] = "manual"
    at: datetime | None = None
    time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    weekday: int = Field(default=1, ge=0, le=6)  # cron: Sunday = 0

    @model_validator(mode="after")
    def valid(self):
        self.title, self.instruction = self.title.strip(), self.instruction.strip()
        self.channels = list(dict.fromkeys(self.channels))
        if not self.title or not self.instruction:
            raise ValueError("Judul dan instruksi wajib diisi")
        if self.schedule == "once" and (not self.at or self.at.tzinfo is None or self.at <= datetime.now(UTC)):
            raise ValueError("Jadwal sekali harus berupa waktu mendatang dengan zona waktu")
        return self


def timing(task: dict, now: datetime | None = None) -> tuple[str | None, str | None]:
    now = now or datetime.now(UTC)
    mode = task["schedule"]
    if mode == "manual":
        return None, None
    if mode == "once":
        at = task["at"]
        return (at.isoformat() if isinstance(at, datetime) else at), None
    if mode in ("every_15m", "hourly"):
        minutes = 15 if mode == "every_15m" else 60
        epoch = int(now.timestamp())
        due = datetime.fromtimestamp((epoch // (minutes * 60) + 1) * minutes * 60, UTC)
        return due.isoformat(), "*/15 * * * *" if minutes == 15 else "0 * * * *"
    hour, minute = map(int, task["time"].split(":"))
    due = now.astimezone(WIB).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if mode == "weekly":
        due += timedelta(days=(task["weekday"] - (due.weekday() + 1) % 7) % 7)
    if due <= now:
        due += timedelta(days=7 if mode == "weekly" else 1)
    return due.astimezone(UTC).isoformat(), f"{minute} {hour} * * {task['weekday'] if mode == 'weekly' else '*'}"


def create_task(store, payload: TaskInput) -> dict:
    task = payload.model_dump(mode="json")
    due, cron = timing(task)
    task.update(id=uuid4().hex, revision=0, status="scheduled" if due else "todo",
                next_run_at=due, cron=cron, timezone="Asia/Jakarta", created_at=now_iso(),
                updated_at=now_iso(), last_run_at=None, result="", events=[])
    if not store.save_agent_task(task):
        raise ValueError("Tugas belum dapat disimpan")
    store.audit("agent_task_created", task["title"], actor="user")
    return task


def change_task(store, task_id: str, operation: str) -> dict:
    task = store.get_agent_task(task_id)
    if task is None:
        raise KeyError(task_id)
    if task["status"] == "running":
        raise ValueError("Tugas masih berjalan; tunggu hasilnya sebelum mengubah status")
    previous = task["revision"]
    if operation == "pause":
        task["status"] = "paused"
    elif operation == "resume":
        task["next_run_at"], task["cron"] = timing(task)
        task["status"] = "scheduled" if task["next_run_at"] else "todo"
    elif operation == "complete":
        task["status"], task["next_run_at"] = "done", None
    else:
        raise ValueError("Operasi tidak dikenal")
    task.update(revision=previous + 1, updated_at=now_iso())
    if not store.save_agent_task(task, previous):
        raise ValueError("Tugas berubah; muat ulang lalu coba lagi")
    store.audit("agent_task_updated", f"{task['title']}: {operation}", actor="user")
    return task


def execute_task(store, task_id: str, tools, agent) -> dict:
    from omnilead.chat import run_chat

    task = store.get_agent_task(task_id)
    if not task or task["status"] not in ("todo", "scheduled", "blocked"):
        raise ValueError("Tugas tidak siap dijalankan")
    previous = task["revision"]
    task.update(status="running", revision=previous + 1, last_run_at=now_iso(), updated_at=now_iso(), events=[], result="")
    if not store.save_agent_task(task, previous):
        raise ValueError("Tugas sudah diambil proses lain")

    def save():
        previous = task["revision"]
        task.update(revision=previous + 1, updated_at=now_iso())
        if not store.save_agent_task(task, previous):
            raise ValueError("Status tugas berubah saat berjalan")

    try:
        if store.get_settings().paused:
            raise ValueError("Agen sedang dijeda di Pengaturan Agen")
        unsupported = set(task["channels"]) - {"instagram"}
        if unsupported:
            raise ValueError("Eksekusi terjadwal belum tersedia untuk: " + ", ".join(sorted(unsupported)))
        instruction = f"Jalankan tugas pada kanal {', '.join(task['channels'])}: {task['instruction']}"
        if tools is not None:
            tools.channel_scope = task["channels"][0]
        failed, used_tool = False, False
        for event in run_chat(tools, agent, store.get_settings().business_name, instruction, [], allow_task_changes=False):
            task["events"] = (task["events"] + [event])[-80:]
            if event["type"] == "error":
                failed, task["result"] = True, event["message"]
            if event["type"] == "tool_result" and not event["ok"]:
                failed = True
            if event["type"] == "tool_result":
                used_tool = True
            if event["type"] == "message":
                task["result"] = event["text"]
            save()
        if not used_tool:
            task["result"] = "Belum ada tool yang dijalankan. " + task["result"]
        if failed or not used_tool:
            task["status"] = "blocked"
        elif task["schedule"] in ("manual", "once"):
            task.update(status="done", next_run_at=None)
        else:
            task["next_run_at"], task["cron"] = timing(task)
            task["status"] = "scheduled"
    except Exception as exc:
        task.update(status="blocked", result=str(exc)[:500])
    save()
    store.audit("agent_task_finished", f"{task['title']}: {task['status']}", actor="agent")
    return task


def run_due_tasks(store, tools, agent, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(UTC)
    completed = []
    if store.get_settings().paused:
        return completed
    for task in store.list_agent_tasks():
        if task["status"] == "running" and task.get("updated_at"):
            # No automatic retry of interrupted external operations.
            if now - datetime.fromisoformat(task["updated_at"]) > timedelta(minutes=30):
                revision = task["revision"]
                task.update(status="blocked", result="Proses terputus; periksa hasil sebelum menjalankan ulang.",
                            revision=revision + 1, updated_at=now.isoformat())
                store.save_agent_task(task, revision)
        if task["status"] != "scheduled" or not task["next_run_at"] or datetime.fromisoformat(task["next_run_at"]) > now:
            continue
        try:
            execute_task(store, task["id"], tools, agent)
            completed.append(task["id"])
        except ValueError:
            pass  # another worker already claimed this occurrence
        if len(completed) >= 5:
            break
    return completed
