"""Local schedule clock; cloud deployments can call /scheduler/agent-tasks."""
import logging
import os
import threading

from omnilead.config import get_settings

log = logging.getLogger(__name__)


def local_worker_enabled() -> bool:
    default = "1" if get_settings().store == "sqlite" else "0"
    return os.environ.get("OMNILEAD_AGENT_TASK_WORKER", default).lower() in ("1", "true", "yes")


def tick():
    from omnilead.agent_tasks import run_due_tasks
    from omnilead.api.deps import (get_accounts, get_agent_client, ingest_for_workspace,
                                   registry_for_workspace, store_for_workspace)
    from omnilead.chat_tools import ChatTools

    workspaces = get_accounts().workspace_ids() if get_settings().auth_enabled else ["legacy"]
    results = {}
    for workspace in workspaces:
        try:
            store = store_for_workspace(workspace)
            tools = ChatTools(store, registry_for_workspace(workspace), ingest_for_workspace(workspace), get_settings(), workspace)
            results[workspace] = run_due_tasks(store, tools, get_agent_client())
        except Exception:
            log.exception("Agent schedule tick failed")
    return results


def start_worker() -> threading.Event:
    stop = threading.Event()
    if not local_worker_enabled():
        return stop

    def run():
        while not stop.wait(15):
            try:
                tick()
            except Exception:
                log.exception("Agent schedule worker failed")

    threading.Thread(target=run, name="agent-task-clock", daemon=True).start()
    return stop
