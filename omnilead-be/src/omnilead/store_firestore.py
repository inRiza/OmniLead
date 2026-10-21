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
import time
from datetime import datetime, timedelta, timezone

from omnilead.models import (
    Action,
    ActionStatus,
    AppSettings,
    AuditEntry,
    Event,
    Lead,
    KnowledgeBase,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
        for name in ("actions", "audit", "leads", "events", "event_keys", "settings", "knowledge"):
            for doc in self._db.collection(name).stream():
                doc.reference.delete()

    # --- actions ---

    def save_action(self, action: Action) -> None:
        self._db.collection("actions").document(action.id).set({
            "data": action.model_dump_json(),
            "status": action.status.value,
            "created_at": action.created_at.isoformat(),
        })

    def get_action(self, action_id: str) -> Action | None:
        snap = self._db.collection("actions").document(action_id).get()
        return Action.model_validate_json(snap.to_dict()["data"]) if snap.exists else None

    def list_actions(self, status: ActionStatus | None = None) -> list[Action]:
        query = self._where("actions", status=status.value) if status else self._db.collection("actions")
        rows = [d.to_dict() for d in query.stream()]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [Action.model_validate_json(r["data"]) for r in rows]

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
        seq = time.time_ns() // 1000  # id urut naik (mikrodetik)
        self._db.collection("audit").document(str(seq)).set({
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

    def list_audit(self, limit: int = 100, channel: str | None = None) -> list[AuditEntry]:
        query = self._where("audit", channel=channel) if channel else self._db.collection("audit")
        rows = [d.to_dict() for d in query.stream()]
        rows.sort(key=lambda r: r["seq"], reverse=True)
        return [self._audit_entry(r) for r in rows[:limit]]

    def count_audit_since(self, event: str, channel: str, since: timedelta) -> int:
        cutoff = (_now() - since).isoformat()
        rows = (d.to_dict() for d in self._where("audit", event=event).stream())
        return sum(1 for r in rows if r["channel"] == channel and r["ts"] >= cutoff)

    # --- leads ---

    def save_lead(self, lead: Lead) -> None:
        self._db.collection("leads").document(lead.id).set({"data": lead.model_dump_json()})

    def get_lead(self, lead_id: str) -> Lead | None:
        snap = self._db.collection("leads").document(lead_id).get()
        return Lead.model_validate_json(snap.to_dict()["data"]) if snap.exists else None

    def delete_lead(self, lead_id: str) -> None:
        self._db.collection("leads").document(lead_id).delete()

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
        for action in self.list_actions():
            if action.lead_id == old_id:
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

    def list_events(self, lead_id: str | None = None, limit: int = 200) -> list[Event]:
        query = self._where("events", lead_id=lead_id) if lead_id else self._db.collection("events")
        rows = [d.to_dict() for d in query.stream()]
        rows.sort(key=lambda r: r["ts"], reverse=True)
        return [Event.model_validate_json(r["data"]) for r in rows[:limit]]

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
