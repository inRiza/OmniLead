from omnilead.approvals.executor import ChannelDisabled, Executor, Paused, RateLimited
from omnilead.approvals.queue import ApprovalQueue, InvalidTransition
from omnilead.autonomy import auto_approvable
from omnilead.models import Action, ActionKind, ActionStatus, Event
from omnilead.store import Store

HOLD_STATUSES = ("block", "warn")


class AutoSender:
    def __init__(self, store: Store, queue: ApprovalQueue, executor: Executor):
        self._store = store
        self._queue = queue
        self._executor = executor

    @property
    def executor(self) -> Executor:
        return self._executor

    @property
    def queue(self) -> ApprovalQueue:
        return self._queue

    def handle(self, action: Action, event: Event | None = None) -> Action:
        settings = self._store.get_settings()
        mode = settings.autonomy
        if mode == "manual" or action.status != ActionStatus.PENDING or action.payload.get("_auto_held"):
            return action
        if action.kind == ActionKind.MERGE:
            if float(action.payload.get("confidence") or 0) < settings.auto_merge_threshold:
                return action
            return self._approve_and_run(action, mode)
        held = [g for g in action.guard if g.status in HOLD_STATUSES]
        if held:
            detail = "; ".join(f"{g.check}: {g.note or g.status}" for g in held)
            return self._hold(action, f"Ditahan untuk tinjauan. {detail}")
        if event is not None and event.status == "review":
            return self._hold(action, "Pesan ditandai untuk tinjauan; tidak dikirim otomatis")
        if not auto_approvable(action, event, mode):
            return action
        return self._approve_and_run(action, mode)

    def _approve_and_run(self, action: Action, mode: str) -> Action:
        try:
            approved = self._queue.auto_approve(action.id, mode)
        except (InvalidTransition, KeyError):
            return self._store.get_action(action.id) or action
        approved.payload = {**approved.payload, "_auto": True}
        self._store.save_action(approved)
        try:
            return self._executor.execute(approved)
        except (Paused, ChannelDisabled, RateLimited) as exc:
            return self._queue.return_to_owner(action.id, str(exc))

    def _hold(self, action: Action, detail: str) -> Action:
        action.payload = {**action.payload, "_auto_held": True}
        self._store.save_action(action)
        self._store.audit("auto_send_held", detail, action.id, actor="agent",
                          channel=action.channel.value, lead_id=action.lead_id)
        return action
