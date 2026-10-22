"""Adapter Firestore dengan antarmuka yang sama seperti `Store` (SQLite).

Koleksi: `actions`, `audit`, `leads`, `events`, `event_keys`, `settings`.
Model disimpan sebagai JSON di field `data`, ditambah field indeks seperlunya.
Query dibatasi pada filter kesetaraan atau satu field supaya tidak butuh
composite index; pengurutan lanjutan dilakukan di Python.

Pilih lewat OMNILEAD_STORE=firestore (+ OMNILEAD_FIRESTORE_PROJECT). Kredensial
memakai Application Default Credentials / service account Cloud Run.

CATATAN: logika diuji dengan fake in-memory (tests/test_firestore_store.py).
Belum diuji terhadap Firestore sungguhan atau emulator.
"""

import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from omnilead.identity import identity_keys
from omnilead.models import (
    Action,
    ActionKind,
    ActionStatus,
    AppSettings,
    AuditEntry,
    Event,
    Lead,
    KnowledgeBase,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


_seq_lock = threading.Lock()
_last_seq = 0


def _next_seq() -> int:
    """Mikrodetik yang selalu naik di proses ini (jam Windows bisa kasar ~1-15 ms)."""
    global _last_seq
    with _seq_lock:
        _last_seq = max(time.time_ns() // 1000, _last_seq + 1)
        return _last_seq


class FirestoreStore:
    def __init__(self, client=None, project: str | None = None, field_filter=None):
        if client is None:
            from google.cloud import firestore

            client = firestore.Client(project=project or None)
        if field_filter is None:
            from google.cloud.firestore_v1.base_query import FieldFilter

            field_filter = FieldFilter
        self._db = client
        self._ff = field_filter
        try:
            from google.api_core.exceptions import AlreadyExists
        except ImportError:  # pragma: no cover
            AlreadyExists = FileExistsError  # type: ignore[assignment,misc]
        self._already_exists = AlreadyExists

    # --- util ---

    def _where(self, collection: str, **equals):
        query = self._db.collection(collection)
        for field, value in equals.items():
            query = query.where(filter=self._ff(field, "==", value))
        return query

    def reset(self) -> None:
        for name in ("actions", "audit", "leads", "events", "event_keys", "settings", "knowledge",
                     "lead_identity", "jobs", "meta", "agent_tasks", "chat_sessions"):
            for doc in self._db.collection(name).stream():
                doc.reference.delete()

    # --- actions ---

    def save_action(self, action: Action) -> None:
        self._db.collection("actions").document(action.id).set({
            "data": action.model_dump_json(),
            "status": action.status.value,
            "created_at": action.created_at.isoformat(),
            "lead_id": action.lead_id,
            "kind": action.kind.value,
        })

    def get_action(self, action_id: str) -> Action | None:
        snap = self._db.collection("actions").document(action_id).get()
        return Action.model_validate_json(snap.to_dict()["data"]) if snap.exists else None

    def list_actions(
        self,
        status: ActionStatus | None = None,
        *,
        lead_id: str | None = None,
        kind: ActionKind | None = None,
        limit: int | None = None,
    ) -> list[Action]:
        equals = {k: v for k, v in (("status", status.value if status else None), ("lead_id", lead_id),
                                    ("kind", kind.value if kind else None)) if v is not None}
        first = next(iter(equals.items()), None)
        query = self._where("actions", **dict([first])) if first else self._db.collection("actions")
        rows = [d.to_dict() for d in query.stream()]
        actions = [Action.model_validate_json(r["data"]) for r in sorted(rows, key=lambda r: r["created_at"], reverse=True)]
        actions = [a for a in actions if (status is None or a.status == status) and (lead_id is None or a.lead_id == lead_id)
                   and (kind is None or a.kind == kind)]
        return actions[:limit] if limit is not None else actions

    # --- audit ---

    def audit(
        self,
        event: str,
        detail: str,
        action_id: str | None = None,
        *,
        actor: str = "system",
        channel: str | None = None,
        lead_id: str | None = None,
    ) -> None:
        seq = _next_seq()
        # sufiks acak: dua instance Cloud Run bisa mendapat seq yang sama
        self._db.collection("audit").document(f"{seq}-{uuid.uuid4().hex[:8]}").set({
            "seq": seq,
            "ts": _now().isoformat(),
            "action_id": action_id,
            "event": event,
            "detail": detail,
            "actor": actor,
            "channel": channel,
            "lead_id": lead_id,
        })

    @staticmethod
    def _audit_entry(r: dict) -> AuditEntry:
        return AuditEntry(
            id=r["seq"], ts=datetime.fromisoformat(r["ts"]), action_id=r["action_id"],
            event=r["event"], detail=r["detail"], actor=r["actor"],
            channel=r["channel"], lead_id=r["lead_id"],
        )

    def list_audit(
        self,
        limit: int = 100,
        channel: str | None = None,
        *,
        lead_id: str | None = None,
        event: str | None = None,
        actor: str | None = None,
        before_id: int | None = None,
    ) -> list[AuditEntry]:
        equals = {k: v for k, v in (("channel", channel), ("lead_id", lead_id), ("event", event), ("actor", actor))
                  if v is not None}
        query = self._where("audit", **equals) if equals else self._db.collection("audit")
        rows = [d.to_dict() for d in query.stream()]
        if before_id is not None:
            rows = [r for r in rows if r["seq"] < before_id]
        rows.sort(key=lambda r: r["seq"], reverse=True)
        return [self._audit_entry(r) for r in rows[:limit]]

    def count_audit_since(self, event: str, channel: str, since: timedelta) -> int:
        cutoff = (_now() - since).isoformat()
        rows = (d.to_dict() for d in self._where("audit", event=event, channel=channel).stream())
        return sum(1 for r in rows if r["ts"] >= cutoff)

    # --- leads ---

    def save_lead(self, lead: Lead) -> None:
        self._db.collection("leads").document(lead.id).set({"data": lead.model_dump_json()})
        self._index_lead(lead)

    @staticmethod
    def _identity_doc(key: str, lead_id: str) -> str:
        return f"{key}|{lead_id}".replace("/", "_")

    def _index_lead(self, lead: Lead) -> None:
        col = self._db.collection("lead_identity")
        keys = identity_keys(lead)
        for doc in self._where("lead_identity", lead_id=lead.id).stream():
            if doc.to_dict()["key"] not in keys:
                doc.reference.delete()
        for key in keys:
            col.document(self._identity_doc(key, lead.id)).set({"key": key, "lead_id": lead.id})

    def _ensure_identity_index(self) -> None:
        marker = self._db.collection("meta").document("identity_index")
        if marker.get().exists:
            return
        for doc in self._db.collection("leads").stream():
            self._index_lead(Lead.model_validate_json(doc.to_dict()["data"]))
        marker.set({"built_at": _now().isoformat()})

    def find_leads_by_identity(self, key: str) -> list[Lead]:
        self._ensure_identity_index()
        ids = {d.to_dict()["lead_id"] for d in self._where("lead_identity", key=key).stream()}
        return [lead for lead in (self.get_lead(i) for i in sorted(ids)) if lead is not None]

    def get_lead(self, lead_id: str) -> Lead | None:
        snap = self._db.collection("leads").document(lead_id).get()
        return Lead.model_validate_json(snap.to_dict()["data"]) if snap.exists else None

    def delete_lead(self, lead_id: str) -> None:
        self._db.collection("leads").document(lead_id).delete()
        for doc in self._where("lead_identity", lead_id=lead_id).stream():
            doc.reference.delete()

    def list_leads(self) -> list[Lead]:
        leads = [Lead.model_validate_json(d.to_dict()["data"]) for d in self._db.collection("leads").stream()]
        leads.sort(
            key=lambda lead: (lead.score if lead.score is not None else -1, lead.updated_at),
            reverse=True,
        )
        return leads

    def reassign_lead(self, old_id: str, new_id: str) -> None:
        for event in self.list_events(lead_id=old_id, limit=10_000):
            event.lead_id = new_id
            self.save_event(event)
        for action in self.list_actions(lead_id=old_id):
            action.lead_id = new_id
            self.save_action(action)

    # --- events ---

    @staticmethod
    def _event_key(channel: str, external_id: str) -> str:
        return f"{channel}:{external_id}".replace("/", "_")

    def find_event(self, channel: str, external_id: str) -> Event | None:
        key = self._db.collection("event_keys").document(self._event_key(channel, external_id)).get()
        if not key.exists:
            return None
        return self.get_event(key.to_dict()["event_id"])

    def get_event(self, event_id: str) -> Event | None:
        snap = self._db.collection("events").document(event_id).get()
        return Event.model_validate_json(snap.to_dict()["data"]) if snap.exists else None

    def save_event(self, event: Event) -> None:
        """Dedup atomik: kunci (kanal, external_id) hanya bisa dibuat sekali."""
        key_ref = self._db.collection("event_keys").document(
            self._event_key(event.channel.value, event.external_id)
        )
        try:
            key_ref.create({"event_id": event.id})
        except self._already_exists:
            if key_ref.get().to_dict().get("event_id") != event.id:
                raise
        self._db.collection("events").document(event.id).set({
            "data": event.model_dump_json(),
            "lead_id": event.lead_id,
            "ts": (event.ts or _now()).isoformat(),
        })

    def list_events(self, lead_id: str | None = None, limit: int = 200, *, before: datetime | None = None) -> list[Event]:
        query = self._where("events", lead_id=lead_id) if lead_id else self._db.collection("events")
        rows = [d.to_dict() for d in query.stream()]
        if before is not None:
            rows = [r for r in rows if r["ts"] < before.isoformat()]
        rows.sort(key=lambda r: r["ts"], reverse=True)
        return [Event.model_validate_json(r["data"]) for r in rows[:limit]]

    def enqueue_job(self, job_id: str, payload: dict) -> bool:
        now = _now().isoformat()
        ref = self._db.collection("jobs").document(job_id.replace("/", "_"))
        try:
            ref.create({"id": job_id, "payload": json.dumps(payload), "status": "pending", "attempts": 0,
                        "error": "", "created_at": now, "updated_at": now})
            return True
        except self._already_exists:
            return False

    def get_job(self, job_id: str) -> dict | None:
        snap = self._db.collection("jobs").document(job_id.replace("/", "_")).get()
        if not snap.exists:
            return None
        row = snap.to_dict()
        return {**row, "payload": json.loads(row["payload"])}

    def list_jobs(self, statuses: tuple[str, ...], older_than: timedelta | None = None, limit: int = 100) -> list[dict]:
        cutoff = (_now() - (older_than or timedelta(0))).isoformat()
        rows = []
        for status in statuses:
            rows += [d.to_dict() for d in self._where("jobs", status=status).stream()]
        rows = sorted((r for r in rows if r["updated_at"] <= cutoff), key=lambda r: r["created_at"])[:limit]
        return [{**r, "payload": json.loads(r["payload"])} for r in rows]

    def update_job(self, job_id: str, status: str, error: str = "", attempt: bool = False) -> None:
        ref = self._db.collection("jobs").document(job_id.replace("/", "_"))
        snap = ref.get()
        if not snap.exists:
            return
        row = snap.to_dict()
        row.update(status=status, error=error[:500], updated_at=_now().isoformat(),
                   attempts=row.get("attempts", 0) + (1 if attempt else 0))
        ref.set(row)

    def list_agent_tasks(self) -> list[dict]:
        return sorted((d.to_dict() for d in self._db.collection("agent_tasks").stream()),
                      key=lambda t: t["created_at"], reverse=True)

    def get_agent_task(self, task_id: str) -> dict | None:
        snap = self._db.collection("agent_tasks").document(task_id).get()
        return snap.to_dict() if snap.exists else None

    def save_agent_task(self, task: dict, expected_revision: int | None = None) -> bool:
        ref = self._db.collection("agent_tasks").document(task["id"])
        if expected_revision is None:
            try:
                ref.create(task)
                return True
            except self._already_exists:
                return False
        from google.cloud import firestore

        @firestore.transactional
        def update(transaction):
            snap = ref.get(transaction=transaction)
            if not snap.exists or snap.to_dict()["revision"] != expected_revision:
                return False
            transaction.set(ref, task)
            return True

        return update(self._db.transaction())

    def list_conversations(self) -> list[dict]:
        return sorted((d.to_dict() for d in self._db.collection("chat_sessions").stream()),
                      key=lambda t: t["updated_at"], reverse=True)

    def get_conversation(self, session_id: str) -> dict | None:
        snap = self._db.collection("chat_sessions").document(session_id).get()
        return snap.to_dict() if snap.exists else None

    def save_conversation(self, session: dict, expected_revision: int | None = None) -> bool:
        ref = self._db.collection("chat_sessions").document(session["id"])
        if expected_revision is None:
            try:
                ref.create(session)
                return True
            except self._already_exists:
                return False
        from google.cloud import firestore

        @firestore.transactional
        def update(transaction):
            snap = ref.get(transaction=transaction)
            if not snap.exists or snap.to_dict()["revision"] != expected_revision:
                return False
            transaction.set(ref, session)
            return True

        return update(self._db.transaction())

    # --- settings ---

    def list_knowledge(self) -> list[KnowledgeBase]:
        return [KnowledgeBase.model_validate_json(d.to_dict()["data"]) for d in self._db.collection("knowledge").stream()]

    def get_knowledge(self, id: str) -> KnowledgeBase | None:
        doc = self._db.collection("knowledge").document(id).get()
        return KnowledgeBase.model_validate_json(doc.to_dict()["data"]) if doc.exists else None

    def save_knowledge(self, knowledge: KnowledgeBase) -> None:
        self._db.collection("knowledge").document(knowledge.id).set({"data": knowledge.model_dump_json()})

    def delete_knowledge(self, id: str) -> None:
        self._db.collection("knowledge").document(id).delete()

    def get_settings(self) -> AppSettings:
        snap = self._db.collection("settings").document("app").get()
        return AppSettings.model_validate(json.loads(snap.to_dict()["value"])) if snap.exists else AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self._db.collection("settings").document("app").set({"value": settings.model_dump_json()})
