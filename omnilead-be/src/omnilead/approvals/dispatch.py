from datetime import datetime, timedelta, timezone

from omnilead.approvals.auto import AutoSender
from omnilead.approvals.executor import ChannelDisabled, Executor, Paused, RateLimited
from omnilead.models import ActionStatus
from omnilead.store import Store

STUCK_AFTER = timedelta(minutes=5)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def dispatch(store: Store, executor: Executor, auto: AutoSender | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    result = {"recovered": [], "retried": [], "executed": [], "auto_sent": []}
    if store.get_settings().paused:
        return {**result, "skipped": "Agen dijeda"}

    for action in store.list_actions(ActionStatus.EXECUTING):
        started = _aware(action.last_attempt_at) or _aware(action.decided_at) or _aware(action.created_at)
        if started and now - started < STUCK_AFTER:
            continue
        action.status = ActionStatus.FAILED
        action.error = "Pengiriman terputus sebelum ada konfirmasi dari platform. Periksa kanal sebelum mencoba ulang."
        action.next_retry_at = None
        store.save_action(action)
        store.audit("execute_interrupted", action.error, action.id, actor="system",
                    channel=action.channel.value, lead_id=action.lead_id)
        result["recovered"].append(action.id)

    for action in store.list_actions(ActionStatus.FAILED):
        due = _aware(action.next_retry_at)
        if due is None or due > now:
            continue
        action.status = ActionStatus.EDITED if action.edited else ActionStatus.APPROVED
        action.next_retry_at = None
        store.save_action(action)
        store.audit("retry", f"Percobaan ulang otomatis ke-{action.attempts + 1}", action.id, actor="scheduler",
                    channel=action.channel.value, lead_id=action.lead_id)
        result["retried"].append(action.id)

    for status in (ActionStatus.APPROVED, ActionStatus.EDITED):
        for action in store.list_actions(status):
            if action.decided_at is None:
                continue
            try:
                done = executor.execute(action)
            except (Paused, ChannelDisabled, RateLimited):
                continue
            if done.status != status:
                result["executed"].append(action.id)

    if auto is not None and store.get_settings().autonomy != "manual":
        for action in store.list_actions(ActionStatus.PENDING):
            event = store.get_event(action.event_id) if action.event_id else None
            done = auto.handle(action, event)
            if done.status != ActionStatus.PENDING:
                result["auto_sent"].append(action.id)
    return result
