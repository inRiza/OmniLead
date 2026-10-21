"""Antrean persetujuan.

Agen hanya memasukkan usulan ke sini (propose). Aksi keluar tidak pernah
dijalankan tanpa salah satu keputusan manusia: approve / edit / reject.
"""

import uuid
from datetime import datetime, timezone

from omnilead.models import Action, ActionStatus, ProposedAction
from omnilead.store import Store


class ApprovalQueue:
    def __init__(self, store: Store):
        self._store = store

    def propose(self, proposal: ProposedAction) -> Action:
        action = Action(
            **proposal.model_dump(),
            id=str(uuid.uuid4()),
            status=ActionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self._store.save_action(action)
        self._store.audit(
            "proposed",
            f"{action.kind} di {action.channel} untuk {action.post_ref}",
            action.id,
        )
        return action

    def pending(self) -> list[Action]:
        return self._store.list_actions(ActionStatus.PENDING)

    def approve(self, action_id: str, edited_text: str | None = None) -> Action:
        action = self._require(action_id)
        if edited_text is not None and edited_text != action.text:
            action.text = edited_text
            action.edited = True
        action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._store.audit(
            "approved" + (" (edited)" if action.edited else ""),
            action.text[:120],
            action.id,
        )
        return action

    def reject(self, action_id: str, reason: str) -> Action:
        action = self._require(action_id)
        action.status = ActionStatus.REJECTED
        action.reject_reason = reason
        action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._store.audit("rejected", reason, action.id)
        return action

    def mark_sent_manually(self, action_id: str) -> Action:
        action = self._require(action_id)
        action.status = ActionStatus.SENT_MANUALLY
        action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._store.audit("sent_manually", "Dikirim sendiri oleh pengguna", action.id)
        return action

    def _require(self, action_id: str) -> Action:
        action = self._store.get_action(action_id)
        if action is None:
            raise KeyError(f"Aksi {action_id} tidak ditemukan")
        return action
