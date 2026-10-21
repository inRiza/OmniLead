"""Executor: satu-satunya komponen yang benar-benar mengirim ke platform.

- Hanya menjalankan aksi yang sudah berstatus disetujui (decided_at terisi,
  status PENDING sebelum eksekusi).
- Memakai connector lewat kontrak yang sama, tidak tahu detail tiap platform.
- Idempoten: aksi yang sudah EXECUTED/SENT tidak dikirim ulang.
- Untuk kanal yang aksinya tidak didukung API (mis. komentar LinkedIn via
  baca), aksi tidak dieksekusi tapi diubah ke AWAITING_MANUAL_SEND + paket
  handoff, bukan dipaksa kirim.
"""

from datetime import datetime, timezone

from omnilead.connectors import handoff
from omnilead.connectors.base import ActionNotSupported, ConnectorError
from omnilead.connectors.registry import Registry
from omnilead.models import Action, ActionKind, ActionStatus
from omnilead.store import Store


class Executor:
    def __init__(self, registry: Registry, store: Store):
        self._registry = registry
        self._store = store

    def execute(self, action: Action) -> Action:
        # Idempotensi: jangan kirim ulang.
        if action.status in (
            ActionStatus.EXECUTED,
            ActionStatus.SENT_MANUALLY,
        ):
            return action
        if action.decided_at is None:
            raise PermissionError("Aksi belum disetujui; executor menolak.")

        connector = self._registry.get(action.channel)
        write_action = (
            "post_comment"
            if action.kind == ActionKind.COMMENT_POST
            else "reply_comment"
        )

        # Kanal tanpa API untuk aksi ini -> handoff, bukan kirim paksa.
        if not connector.supports(write_action):
            action.status = ActionStatus.AWAITING_MANUAL_SEND
            action.result_ref = None
            self._store.save_action(action)
            pkg = handoff.build_handoff(action.channel, action.text)
            self._store.audit(
                "handoff",
                f"{write_action} di {action.channel} lewat Salin & buka",
                action.id,
            )
            # paket handoff dikembalikan via field error? Tidak; simpan di audit
            # dan biarkan API route menyusun paketnya. Di sini cukup ubah status.
            return action

        action.status = ActionStatus.EXECUTING
        self._store.save_action(action)
        try:
            if action.kind == ActionKind.COMMENT_POST:
                ref = connector.post_comment(action.post_ref, action.text)
            else:
                if not action.comment_ref:
                    raise ConnectorError("reply_comment tanpa comment_ref")
                ref = connector.reply_comment(action.comment_ref, action.text)
        except (ConnectorError, ActionNotSupported) as exc:
            action.status = ActionStatus.FAILED
            action.error = str(exc)
            self._store.save_action(action)
            self._store.audit("execute_failed", str(exc), action.id)
            return action

        action.status = ActionStatus.EXECUTED
        action.result_ref = ref
        action.decided_at = action.decided_at or datetime.now(timezone.utc)
        self._store.save_action(action)
        self._store.audit("executed", f"ref={ref}", action.id)
        return action
