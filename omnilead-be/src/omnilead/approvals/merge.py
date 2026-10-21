"""Pisah profil: membatalkan merge identitas yang sudah dieksekusi.

Saat merge dieksekusi, executor menyimpan snapshot (`payload["undo"]`): profil
sumber utuh, kondisi tujuan sebelum digabung, serta ID event dan aksi yang
dipindahkan. Pemisahan mengembalikan semuanya, tanpa menghapus identitas baru
yang masuk ke profil tujuan setelah merge.
"""

from datetime import datetime, timezone

from omnilead.approvals.queue import InvalidTransition
from omnilead.models import Action, ActionKind, ActionStatus, Lead
from omnilead.store import Store

LIST_FIELDS = ("phones", "emails", "handles")


def build_snapshot(store: Store, src: Lead, dst: Lead, action_id: str) -> dict:
    return {
        "source": src.model_dump(mode="json"),
        "target_before": dst.model_dump(mode="json"),
        "event_ids": [e.id for e in store.list_events(lead_id=src.id, limit=100_000)],
        "action_ids": [
            a.id for a in store.list_actions() if a.lead_id == src.id and a.id != action_id
        ],
    }


def can_undo(action: Action) -> bool:
    return (
        action.kind == ActionKind.MERGE
        and action.status == ActionStatus.EXECUTED
        and "undo" in action.payload
        and not action.payload.get("undone")
    )


def undo_merge(store: Store, action_id: str) -> Action:
    action = store.get_action(action_id)
    if action is None:
        raise KeyError(action_id)
    if not can_undo(action):
        raise InvalidTransition(
            "Hanya merge yang sudah dieksekusi dan belum dipisah yang bisa dibatalkan"
        )

    snap = action.payload["undo"]
    source = Lead.model_validate(snap["source"])
    before = Lead.model_validate(snap["target_before"])
    target = store.get_lead(str(action.payload.get("target_lead_id", "")))
    if target is None:
        raise InvalidTransition("Profil tujuan sudah tidak ada; tidak bisa dipisah")
    if store.get_lead(source.id) is not None:
        raise InvalidTransition("Profil sumber sudah ada kembali; tidak bisa dipisah")

    # Tujuan: buang identitas yang berasal dari sumber, simpan yang masuk sesudah merge.
    for field in LIST_FIELDS:
        from_source = set(getattr(source, field)) - set(getattr(before, field))
        setattr(target, field, [v for v in getattr(target, field) if v not in from_source])
    target.name, target.company = before.name, before.company
    target.score, target.label = before.score, before.label
    target.score_reason = before.score_reason
    target.updated_at = datetime.now(timezone.utc)
    store.save_lead(target)
    store.save_lead(source)

    for event_id in snap["event_ids"]:
        event = store.get_event(event_id)
        if event and event.lead_id == target.id:
            event.lead_id = source.id
            store.save_event(event)
    for aid in snap["action_ids"]:
        moved = store.get_action(aid)
        if moved and moved.lead_id == target.id:
            moved.lead_id = source.id
            store.save_action(moved)

    action.payload = {**action.payload, "undone": True}
    action.result_ref = f"split:{target.id}->{source.id}"
    store.save_action(action)
    store.audit(
        "identity_split",
        f"Pemilik memisahkan kembali {source.name} dari {before.name}",
        action.id,
        actor="owner",
        channel=action.channel.value,
        lead_id=target.id,
    )
    return action
