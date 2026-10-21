"""Pekerjaan terjadwal (dipicu Cloud Scheduler) dan ringkasan harian.

Follow-up: aksi `followup` yang sudah disetujui dan jatuh tempo diubah menjadi
USULAN pesan baru (pending). Tidak pernah dikirim otomatis; pemilik tetap
menyetujui. Jika pelanggan sudah membalas sejak pengingat dibuat, follow-up
dilewati.
"""

from datetime import datetime, timedelta, timezone

from omnilead.approvals.queue import ApprovalQueue
from omnilead.models import (
    Action,
    ActionKind,
    ActionStatus,
    ProposedAction,
)
from omnilead.store import Store

IDLE_HOT = timedelta(hours=24)
OPEN_STATUSES = (ActionStatus.PENDING, ActionStatus.AWAITING_MANUAL_SEND, ActionStatus.FAILED)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def run_followups(
    store: Store, queue: ApprovalQueue, now: datetime | None = None
) -> dict:
    now = now or datetime.now(timezone.utc)
    created: list[str] = []
    skipped: list[str] = []

    for action in store.list_actions():
        if (
            action.kind != ActionKind.FOLLOWUP
            or action.status != ActionStatus.EXECUTED
            or action.payload.get("fired")
            or action.due_at is None
            or _aware(action.due_at) > now  # type: ignore[operator]
        ):
            continue

        replied = any(
            e.ts and _aware(e.ts) > _aware(action.created_at)  # type: ignore[operator]
            for e in store.list_events(lead_id=action.lead_id, limit=100)
        ) if action.lead_id else False

        action.payload = {**action.payload, "fired": True, "skipped_replied": replied}
        store.save_action(action)

        if replied:
            skipped.append(action.id)
            store.audit(
                "followup_skipped",
                "Pelanggan sudah membalas; follow-up dilewati",
                action.id,
                actor="scheduler",
                channel=action.channel.value,
                lead_id=action.lead_id,
            )
            continue

        proposal = queue.propose(
            ProposedAction(
                channel=action.channel,
                kind=ActionKind.SEND_MESSAGE,
                post_ref=action.post_ref,
                text=action.text,
                recipient=action.recipient,
                reason="Follow-up jatuh tempo dan belum ada balasan dari pelanggan",
                lead_id=action.lead_id,
                event_id=action.event_id,
                payload={"role": "followup_due", "from_action": action.id},
            )
        )
        created.append(proposal.id)
        store.audit(
            "followup_due",
            "Follow-up jatuh tempo; usulan pesan dibuat",
            proposal.id,
            actor="scheduler",
            channel=action.channel.value,
            lead_id=action.lead_id,
        )
    return {"created": created, "skipped": skipped}


def daily_summary(store: Store, now: datetime | None = None, limit: int = 5) -> list[dict]:
    """'5 hal yang perlu ditangani hari ini', urut prioritas."""
    now = now or datetime.now(timezone.utc)
    actions = store.list_actions()
    items: list[dict] = []

    for a in actions:
        if a.status == ActionStatus.FAILED:
            items.append({
                "priority": 0, "kind": "failed", "lead_id": a.lead_id, "action_id": a.id,
                "title": "Aksi gagal dikirim",
                "detail": a.error or "Coba ulang atau tangani manual",
            })

    for e in store.list_events(limit=300):
        if e.status in ("agent_error", "held"):
            items.append({
                "priority": 1, "kind": e.status, "lead_id": e.lead_id, "event_id": e.id,
                "title": "Pesan belum dianalisis agen",
                "detail": e.review_reason or e.text[:80],
            })
        elif e.status == "review":
            items.append({
                "priority": 1, "kind": "review", "lead_id": e.lead_id, "event_id": e.id,
                "title": "Perlu ditinjau manual", "detail": e.review_reason or e.text[:80],
            })

    open_by_lead: dict[str | None, int] = {}
    for a in actions:
        if a.status in OPEN_STATUSES and a.status != ActionStatus.FAILED:
            open_by_lead[a.lead_id] = open_by_lead.get(a.lead_id, 0) + 1

    for lead in store.list_leads():
        waiting = open_by_lead.get(lead.id, 0)
        if lead.label == "Hot" and waiting:
            items.append({
                "priority": 2, "kind": "hot_waiting", "lead_id": lead.id,
                "title": f"Lead panas: {lead.name}",
                "detail": f"{waiting} aksi menunggu persetujuan Anda",
            })
        elif lead.label == "Hot" and now - _aware(lead.updated_at) > IDLE_HOT:  # type: ignore[operator]
            items.append({
                "priority": 2, "kind": "hot_idle", "lead_id": lead.id,
                "title": f"Lead panas terbengkalai: {lead.name}",
                "detail": "Tanpa aktivitas lebih dari 24 jam",
            })

    due = [
        a for a in actions
        if a.kind == ActionKind.FOLLOWUP and a.status == ActionStatus.EXECUTED
        and not a.payload.get("fired") and a.due_at and _aware(a.due_at) <= now  # type: ignore[operator]
    ]
    for a in due:
        items.append({
            "priority": 3, "kind": "followup_due", "lead_id": a.lead_id, "action_id": a.id,
            "title": "Follow-up jatuh tempo", "detail": a.text[:80],
        })

    items.sort(key=lambda i: i["priority"])
    return items[:limit]


__all__ = ["run_followups", "daily_summary", "Action"]
