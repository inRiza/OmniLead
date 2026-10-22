"""Executor koneksi API. Input browser lokal memiliki persetujuan langkah sendiri.

- Hanya menjalankan aksi berstatus APPROVED/EDITED (hasil keputusan manusia).
- Menolak selama Pause aktif, kanal dimatikan, atau batas laju terlampaui;
  aksi tetap tertahan dan bisa dijalankan lagi nanti.
- Dry-run: aksi dicatat sebagai terkirim tanpa memanggil platform.
- Idempoten: aksi yang sudah selesai tidak dikirim ulang.
- Aksi yang tidak didukung API (mis. DM, WhatsApp, email tanpa koneksi) tidak
  dipaksa kirim; statusnya menjadi AWAITING_MANUAL_SEND (Salin & buka).
- crm_update dan followup bersifat internal: diterapkan ke data sendiri.
"""

from datetime import datetime, timedelta, timezone

from omnilead.connectors.base import ActionNotSupported, ConnectorError, TransientError
from omnilead.connectors.registry import Registry
from omnilead.approvals.merge import build_snapshot
from omnilead.models import EXTERNAL_KINDS, Action, ActionKind, ActionStatus, set_stage
from omnilead.store import Store
from omnilead.windows import check_window

DONE = (
    ActionStatus.EXECUTED,
    ActionStatus.SENT_MANUALLY,
    ActionStatus.AWAITING_MANUAL_SEND,
)
RUNNABLE = (ActionStatus.APPROVED, ActionStatus.EDITED)
RETRY_BACKOFF = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))

WRITE_ACTION = {
    ActionKind.COMMENT_POST: "post_comment",
    ActionKind.REPLY_COMMENT: "reply_comment",
    ActionKind.SEND_MESSAGE: "send_message",
}


class Paused(Exception):
    """Agent dijeda. Semua aksi ditahan."""


class ChannelDisabled(Exception):
    """Saklar kanal mati."""


class RateLimited(Exception):
    """Batas pengiriman per jam untuk kanal ini terlampaui."""


class Executor:
    def __init__(self, registry: Registry, store: Store):
        self._registry = registry
        self._store = store

    def execute(self, action: Action) -> Action:
        if action.status in DONE:
            return action  # idempoten
        if action.status not in RUNNABLE or action.decided_at is None:
            raise PermissionError("Aksi belum disetujui; executor menolak.")

        settings = self._store.get_settings()
        if settings.paused:
            self._log(action, "blocked_paused", "Agent dijeda; aksi ditahan")
            raise Paused("Agent dijeda. Semua aksi ditahan.")

        if action.kind not in EXTERNAL_KINDS:
            return self._execute_internal(action)

        if action.channel in settings.disabled_channels:
            self._log(action, "blocked_channel", f"Kanal {action.channel.value} dimatikan")
            raise ChannelDisabled(f"Kanal {action.channel.value} dimatikan")

        sent_last_hour = sum(
            self._store.count_audit_since(kind, action.channel.value, timedelta(hours=1))
            for kind in ("executed", "dry_run")
        )
        if sent_last_hour >= settings.rate_limit_per_hour:
            self._log(action, "blocked_rate_limit", f"{sent_last_hour} pengiriman/jam")
            raise RateLimited(
                f"Batas {settings.rate_limit_per_hour} pengiriman/jam untuk {action.channel.value} tercapai"
            )

        source = self._store.get_event(action.event_id) if action.event_id else None
        if source and source.meta.get("transport") == "browser":
            action.status = ActionStatus.AWAITING_MANUAL_SEND
            action.result_ref = None
            self._store.save_action(action)
            self._log(action, "handoff", "Pesan berasal dari browser; draf ditinjau dan dikirim melalui sesi browser yang sesuai.")
            return action

        connector = self._registry.get(action.channel)
        write_action = WRITE_ACTION[action.kind]

        source = self._store.get_event(action.event_id) if action.event_id else None
        if (source and source.meta.get("handoff_only")) or not connector.supports(write_action):
            action.status = ActionStatus.AWAITING_MANUAL_SEND
            action.result_ref = None
            self._store.save_action(action)
            self._log(
                action, "handoff", f"{write_action} di {action.channel.value} lewat Salin & buka"
            )
            return action

        window = check_window(self._store, action)
        if not window.open:
            return self._fail(action, window.reason)

        bindings = getattr(self._registry, "account_ids", None)
        if bindings is not None and action.payload.get("_connection_account") != bindings.get(action.channel.value, ""):
            return self._fail(action, "Akun kanal telah diganti sejak draf dibuat. Analisis ulang pesan sebelum mengirim.")

        if settings.dry_run:
            action.status = ActionStatus.EXECUTED
            action.result_ref = "dry-run"
            self._store.save_action(action)
            self._log(action, "dry_run", "Dry-run: tidak dikirim ke platform", actor="executor")
            return action

        now = datetime.now(timezone.utc)
        action.status = ActionStatus.EXECUTING
        action.attempts += 1
        action.last_attempt_at = now
        action.next_retry_at = None
        self._store.save_action(action)
        try:
            ref = self._send(connector, action)
        except TransientError as exc:
            return self._fail(action, str(exc), retry=True)
        except (ConnectorError, ActionNotSupported) as exc:
            return self._fail(action, str(exc))
        except Exception as exc:
            return self._fail(action, f"Kesalahan tak terduga saat mengirim: {exc}")

        action.status = ActionStatus.EXECUTED
        action.result_ref = ref
        action.error = None
        action.delivery_status = "sent"
        action.delivery_at = now
        self._store.save_action(action)
        self._log(action, "executed", f"ref={ref}", actor="executor")
        return action

    # --- internal ---

    def _send(self, connector, action: Action) -> str:
        if action.kind == ActionKind.COMMENT_POST:
            return connector.post_comment(action.post_ref, action.text)
        if action.kind == ActionKind.REPLY_COMMENT:
            if not action.comment_ref:
                raise ConnectorError("reply_comment tanpa comment_ref")
            return connector.reply_comment(action.comment_ref, action.text)
        if not action.recipient:
            raise ConnectorError("send_message tanpa penerima")
        return connector.send_message(
            action.recipient, action.text, action.comment_ref, self._context(action)
        )

    def _context(self, action: Action) -> dict:
        """Metadata kanal dari pesan masuk terakhir lead (mis. thread Gmail)."""
        if action.event_id:
            event = self._store.get_event(action.event_id)
            if event and event.channel == action.channel:
                return event.meta
        if not action.lead_id:
            return {}
        for e in self._store.list_events(lead_id=action.lead_id, limit=50):
            if e.channel == action.channel and e.meta:
                return e.meta
        return {}

    def _execute_internal(self, action: Action) -> Action:
        if action.kind == ActionKind.MERGE:
            return self._execute_merge(action)
        if action.kind == ActionKind.CRM_UPDATE:
            lead = self._store.get_lead(action.lead_id) if action.lead_id else None
            if lead is None:
                return self._fail(action, "crm_update tanpa lead yang valid")
            stage = str(action.payload.get("stage", lead.stage))
            now = datetime.now(timezone.utc)
            set_stage(lead, stage, now)
            lead.tags = list(dict.fromkeys([*lead.tags, *(str(t) for t in action.payload.get("tags", []))]))
            lead.updated_at = now
            self._store.save_lead(lead)
            ref = f"crm:{stage}"
        else:  # FOLLOWUP: pengingat terjadwal; pengiriman saat jatuh tempo lewat usulan baru
            due = action.due_at.isoformat() if action.due_at else "tanpa-tenggat"
            ref = f"scheduled:{due}"
        action.status = ActionStatus.EXECUTED
        action.result_ref = ref
        self._store.save_action(action)
        self._log(action, "executed_internal", ref, actor="executor")
        return action

    def _execute_merge(self, action: Action) -> Action:
        src = self._store.get_lead(str(action.payload.get("source_lead_id", "")))
        dst = self._store.get_lead(str(action.payload.get("target_lead_id", "")))
        if src is None or dst is None or src.id == dst.id:
            return self._fail(action, "merge: profil sumber/tujuan tidak valid atau sudah digabung")

        action.payload = {**action.payload, "undo": build_snapshot(self._store, src, dst, action.id)}
        for field in ("phones", "emails", "handles"):
            merged = getattr(dst, field)
            merged += [v for v in getattr(src, field) if v not in merged]
        confidence = float(action.payload.get("confidence") or 1.0)
        merged_at = datetime.now(timezone.utc).isoformat()
        for key, meta in src.identity_sources.items():
            dst.identity_sources.setdefault(key, {**meta, "source": "merge", "confidence": confidence,
                                                  "merged_from": src.id, "at": merged_at})
        dst.name = dst.name or src.name
        dst.company = dst.company or src.company
        if (src.score or -1) > (dst.score or -1):
            dst.score, dst.label, dst.score_reason = src.score, src.label, src.score_reason
        dst.updated_at = datetime.now(timezone.utc)
        self._store.save_lead(dst)
        self._store.reassign_lead(src.id, dst.id)
        self._store.delete_lead(src.id)

        evidence = "; ".join(str(x) for x in action.payload.get("evidence", []))
        action.lead_id = dst.id
        action.status = ActionStatus.EXECUTED
        action.result_ref = f"merged:{src.id}->{dst.id}"
        self._store.save_action(action)
        auto = bool(action.payload.get("_auto"))
        self._store.audit(
            "identity_merged",
            f"{'Digabung otomatis oleh agen' if auto else 'Disetujui pemilik'}: {src.name} digabung ke {dst.name}. Bukti: {evidence}",
            action.id,
            actor="agent" if auto else "owner",
            channel=action.channel.value,
            lead_id=dst.id,
        )
        return action

    def _fail(self, action: Action, error: str, retry: bool = False) -> Action:
        action.status = ActionStatus.FAILED
        action.error = error
        detail = error
        if retry and action.attempts <= len(RETRY_BACKOFF):
            action.next_retry_at = datetime.now(timezone.utc) + RETRY_BACKOFF[action.attempts - 1]
            detail = f"{error}. Dicoba ulang otomatis pukul {action.next_retry_at.strftime('%H:%M')} UTC"
        else:
            action.next_retry_at = None
        self._store.save_action(action)
        self._log(action, "execute_failed", detail, actor="executor")
        return action

    def _log(self, action: Action, event: str, detail: str, actor: str = "executor") -> None:
        self._store.audit(
            event,
            detail,
            action.id,
            actor=actor,
            channel=action.channel.value,
            lead_id=action.lead_id,
        )
