"""Workspace scoped agent board, manual runs, and schedules."""
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from omnilead.agent_tasks import TaskInput, change_task, create_task, execute_task
from omnilead.api.deps import get_agent_client, get_ingest, get_registry, get_store, workspace_for_request
from omnilead.chat_tools import ChatTools
from omnilead.config import get_settings

router = APIRouter(prefix="/agent/tasks", tags=["agent tasks"])


@router.get("")
def tasks(store=Depends(get_store)):
    from omnilead.task_worker import local_worker_enabled
    return {"tasks": store.list_agent_tasks(), "scheduler": "local" if local_worker_enabled() else "external",
            "timezone": "Asia/Jakarta", "supported_channels": ["instagram"]}


@router.post("", status_code=201)
def add_task(payload: TaskInput, store=Depends(get_store)):
    if len(store.list_agent_tasks()) >= 200:
        raise HTTPException(409, "Batas 200 tugas per bisnis tercapai")
    return create_task(store, payload)


class TaskChange(BaseModel):
    operation: Literal["pause", "resume", "complete"]


@router.patch("/{task_id}")
def update_task(task_id: str, payload: TaskChange, store=Depends(get_store)):
    try:
        return change_task(store, task_id, payload.operation)
    except KeyError:
        raise HTTPException(404, "Tugas tidak ditemukan")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post("/{task_id}/run", status_code=202)
def start_task(task_id: str, request: Request, background: BackgroundTasks, store=Depends(get_store),
               registry=Depends(get_registry), ingest=Depends(get_ingest), agent=Depends(get_agent_client)):
    task = store.get_agent_task(task_id)
    if not task:
        raise HTTPException(404, "Tugas tidak ditemukan")
    if task["status"] not in ("todo", "scheduled", "blocked"):
        raise HTTPException(409, "Tugas tidak siap dijalankan")
    if store.get_settings().paused:
        raise HTTPException(423, "Agen sedang dijeda")
    tools = ChatTools(store, registry, ingest, get_settings(), workspace_for_request(request))

    def run():
        try:
            execute_task(store, task_id, tools, agent)
        except ValueError:
            pass  # claimed by another worker between request and background execution

    background.add_task(run)
    return {"accepted": True, "task_id": task_id}
