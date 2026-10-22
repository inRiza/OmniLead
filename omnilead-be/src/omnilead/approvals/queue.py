"""Antrean persetujuan.

Agen hanya memasukkan usulan ke sini (propose). Aksi keluar tidak pernah
dijalankan tanpa keputusan manusia: approve / edit / reject.

Transisi sah:
  pending              -> approved | edited | rejected
  awaiting_manual_send -> sent_manually
Selain itu ditolak dengan InvalidTransition (HTTP 409).
"""

import uuid
from datetime import datetime, timezone

from omnilead.models import Action, ActionStatus, ProposedAction
from omnilead.store import Store

MAX_PREFERENCES = 20


class InvalidTransition(Exception):
    """Aksi tidak berada di status yang mengizinkan transisi ini."""


class ApprovalQueue:
    def __init__(self, store: Store, actor: str = "owner", account_bindings: dict | None = None):
        self._store = store
        self.actor = actor
        self.account_bindings = account_bindings

    def propose(self, proposal: ProposedAction) -> Action:
        if self.account_bindings is not None:
            account = self.account_bindings.get(proposal.channel.value, "")
            event = self._store.get_event(proposal.event_id) if proposal.event_id else None
            if event and event.channel == proposal.channel and "business_account_id" in event.meta:
                account = event.meta["business_account_id"]
            proposal = proposal.model_copy(update={"payload": {**proposal.payload, "_connection_account": account}})
        action = Action(
            **proposal.model_dump(),
            id=str(uuid.uuid4()),
            status=ActionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self._store.save_action(action)
        self._store.audit(
            "proposed",
            f"{action.kind.value} di {action.channel.value} untuk {action.post_ref or action.recipient or '-'}",
            action.id,
            actor="agent",
            channel=action.channel.value,
            lead_id=action.lead_id,
        )
        return action

    def pending(self) -> list[Action]:
        return self._store.list_actions(ActionStatus.PENDING)

    def approve(self, action_id: str, edited_text: str | None = None) -> Action:
        action = self._require(action_id)
        self._expect(action, ActionStatus.PENDING, "disetujui")
        if edited_text is not None and edited_text != action.text:
            action.text = edited_text
            action.edited = True
        action.status = ActionStatus.EDITED if action.edited else ActionStatus.APPROVED
        action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._audit(
            action,
            "approved" + (" (edited)" if action.edited else ""),
            action.text[:120],
            actor="owner",
        )
        return action

    def approve_auto(self, action_id: str) -> Action:
        action = self._require(action_id)
        self._expect(action, ActionStatus.PENDING, "dikirim otomatis")
        action.status = ActionStatus.APPROVED
        action.decided_at = datetime.now(timezone.utc)
        action.payload = {**action.payload, "_auto": True}
        self._store.save_action(action)
        self._audit(action, "auto_approved", action.text[:120] or action.kind.value, actor="agent")
        return action

    def feedback(self, action_id: str, rating: str, reason: str) -> Action:
        action = self._require(action_id)
        entry = {"rating": rating, "reason": reason.strip(), "by": self.actor, "at": datetime.now(timezone.utc).isoformat()}
        action.feedback = [*action.feedback, entry][-10:]
        if rating == "bad" and action.status == ActionStatus.PENDING:
            action.status = ActionStatus.REJECTED
            action.reject_reason = reason
            action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._audit(action, "feedback_" + rating, reason or "-", actor="owner")
        if rating == "bad":
            self._learn_preference(reason)
        return action

    def reject(self, action_id: str, reason: str) -> Action:
        action = self._require(action_id)
        self._expect(action, ActionStatus.PENDING, "ditolak")
        action.status = ActionStatus.REJECTED
        action.reject_reason = reason
        action.decided_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._audit(action, "rejected", reason, actor="owner")
        self._learn_preference(reason)
        return action

    def mark_sent_manually(self, action_id: str) -> Action:
        action = self._require(action_id)
        self._expect(action, ActionStatus.AWAITING_MANUAL_SEND, "ditandai terkirim manual")
        action.status = ActionStatus.SENT_MANUALLY
        self._store.save_action(action)
        self._audit(action, "sent_manually", "Dikirim sendiri oleh pengguna", actor="owner")
        return action

    def retry(self, action_id: str) -> Action:
        """Ulangi aksi yang gagal kirim. Keputusan manusia sebelumnya tetap berlaku."""
        action = self._require(action_id)
        self._expect(action, ActionStatus.FAILED, "dicoba ulang")
        action.status = ActionStatus.EDITED if action.edited else ActionStatus.APPROVED
        action.error = None
        action.next_retry_at = None
        self._store.save_action(action)
        self._audit(action, "retry", "Dicoba ulang oleh pengguna", actor="owner")
        return action

    # --- internal ---

    def _learn_preference(self, reason: str) -> None:
        """Alasan penolakan jadi preferensi bisnis yang dimuat pada draf berikutnya."""
        reason = reason.strip()
        if not reason:
            return
        settings = self._store.get_settings()
        if reason in settings.preferences:
            return
        settings.preferences = (settings.preferences + [reason])[-MAX_PREFERENCES:]
        self._store.save_settings(settings)
        self._store.audit("preference_learned", reason, actor="system")

    def _audit(self, action: Action, event: str, detail: str, actor: str) -> None:
        self._store.audit(
            event,
            detail,
            action.id,
            actor=self.actor if actor == "owner" else actor,
            channel=action.channel.value,
            lead_id=action.lead_id,
        )

    @staticmethod
    def _expect(action: Action, expected: ActionStatus, verb: str) -> None:
        if action.status != expected:
            raise InvalidTransition(
                f"Aksi berstatus {action.status.value}; hanya status {expected.value} yang bisa {verb}"
            )

    def _require(self, action_id: str) -> Action:
        action = self._store.get_action(action_id)
        if action is None:
            raise KeyError(f"Aksi {action_id} tidak ditemukan")
        return action
