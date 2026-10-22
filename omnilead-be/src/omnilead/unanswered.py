"""Delivery evidence for incoming messages; unread and draft status are separate."""
from datetime import timezone

from omnilead.models import ActionKind, ActionStatus

SENT = {ActionStatus.EXECUTED, ActionStatus.SENT_MANUALLY}


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def reply_state(event, actions) -> str:
    """Return answered/unanswered; pending drafts never count as replies."""
    for action in actions:
        if action.channel != event.channel or action.status not in SENT or action.result_ref == "dry-run":
            continue
        if action.kind not in (ActionKind.SEND_MESSAGE, ActionKind.REPLY_COMMENT):
            continue
        if event.kind == "comment":
            if action.event_id == event.id or (event.comment_ref and action.comment_ref == event.comment_ref):
                return "answered"
            continue
        if action.kind != ActionKind.SEND_MESSAGE:
            continue
        if action.event_id == event.id:
            return "answered"
        sent_at = action.delivery_at or action.last_attempt_at or action.decided_at or action.created_at
        if event.ts and _aware(sent_at) >= _aware(event.ts):
            return "answered"
    history = event.meta.get("conversation") or []
    if history and isinstance(history[-1], dict) and history[-1].get("direction") == "out":
        return "answered"
    return "unanswered"


def pending_drafts(event, actions):
    return [a for a in actions if a.event_id == event.id and a.kind in (
        ActionKind.SEND_MESSAGE, ActionKind.REPLY_COMMENT) and a.status in (
        ActionStatus.PENDING, ActionStatus.APPROVED, ActionStatus.EDITED,
        ActionStatus.EXECUTING, ActionStatus.AWAITING_MANUAL_SEND)]
