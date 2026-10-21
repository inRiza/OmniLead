"""Penyimpanan SQLite untuk aksi, audit, lead, event, dan pengaturan.

Cukup untuk dev dan demo; restart server tidak kehilangan data. Antarmuka
metode di sini yang dipakai seluruh BE, sehingga adapter Firestore untuk
produksi cukup mengimplementasikan metode yang sama.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from omnilead.models import (
    Action,
    ActionStatus,
    AppSettings,
    AuditEntry,
    Event,
    Lead,
    KnowledgeBase,
)


class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                action_id TEXT,
                event TEXT NOT NULL,
                detail TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'system',
                channel TEXT,
                lead_id TEXT
            );
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                external_id TEXT NOT NULL,
                lead_id TEXT,
                ts TEXT NOT NULL,
                data TEXT NOT NULL,
                UNIQUE (channel, external_id)
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            );
            """
        )
        # DB lama (sebelum kolom audit diperluas)
        cols = {r["name"] for r in self._db.execute("PRAGMA table_info(audit)")}
        for col, ddl in (
            ("actor", "TEXT NOT NULL DEFAULT 'system'"),
            ("channel", "TEXT"),
            ("lead_id", "TEXT"),
        ):
            if col not in cols:
                self._db.execute(f"ALTER TABLE audit ADD COLUMN {col} {ddl}")
        self._db.commit()

    def reset(self) -> None:
        """Hapus semua data (dipakai skrip seed)."""
        for table in ("actions", "audit", "leads", "events", "settings", "knowledge"):
            self._db.execute(f"DELETE FROM {table}")
        self._db.commit()

    # --- actions ---

    def save_action(self, action: Action) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO actions (id, data, status, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                action.id,
                action.model_dump_json(),
                action.status.value,
                action.created_at.isoformat(),
            ),
        )
        self._db.commit()

    def get_action(self, action_id: str) -> Action | None:
        row = self._db.execute(
            "SELECT data FROM actions WHERE id = ?", (action_id,)
        ).fetchone()
        return Action.model_validate_json(row["data"]) if row else None

    def list_actions(self, status: ActionStatus | None = None) -> list[Action]:
        if status:
            rows = self._db.execute(
                "SELECT data FROM actions WHERE status = ? ORDER BY created_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT data FROM actions ORDER BY created_at DESC"
            ).fetchall()
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
        self._db.execute(
            "INSERT INTO audit (ts, action_id, event, detail, actor, channel, lead_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                action_id,
                event,
                detail,
                actor,
                channel,
                lead_id,
            ),
        )
        self._db.commit()

    def list_audit(
        self, limit: int = 100, channel: str | None = None
    ) -> list[AuditEntry]:
        if channel:
            rows = self._db.execute(
                "SELECT * FROM audit WHERE channel = ? ORDER BY id DESC LIMIT ?",
                (channel, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            AuditEntry(
                id=r["id"],
                ts=datetime.fromisoformat(r["ts"]),
                action_id=r["action_id"],
                event=r["event"],
                detail=r["detail"],
                actor=r["actor"],
                channel=r["channel"],
                lead_id=r["lead_id"],
            )
            for r in rows
        ]

    def count_audit_since(self, event: str, channel: str, since: timedelta) -> int:
        cutoff = (datetime.now(timezone.utc) - since).isoformat()
        row = self._db.execute(
            "SELECT COUNT(*) AS n FROM audit WHERE event = ? AND channel = ? AND ts >= ?",
            (event, channel, cutoff),
        ).fetchone()
        return int(row["n"])

    # --- leads ---

    def save_lead(self, lead: Lead) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO leads (id, data) VALUES (?, ?)",
            (lead.id, lead.model_dump_json()),
        )
        self._db.commit()

    def get_lead(self, lead_id: str) -> Lead | None:
        row = self._db.execute(
            "SELECT data FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()
        return Lead.model_validate_json(row["data"]) if row else None

    def delete_lead(self, lead_id: str) -> None:
        self._db.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        self._db.commit()

    def reassign_lead(self, old_id: str, new_id: str) -> None:
        """Pindahkan semua event dan aksi dari satu lead ke lead lain (saat merge)."""
        for event in self.list_events(lead_id=old_id, limit=10_000):
            event.lead_id = new_id
            self.save_event(event)
        for action in self.list_actions():
            if action.lead_id == old_id:
                action.lead_id = new_id
                self.save_action(action)

    def list_leads(self) -> list[Lead]:
        rows = self._db.execute("SELECT data FROM leads").fetchall()
        leads = [Lead.model_validate_json(r["data"]) for r in rows]
        leads.sort(
            key=lambda lead: (lead.score if lead.score is not None else -1, lead.updated_at),
            reverse=True,
        )
        return leads

    # --- events ---

    def find_event(self, channel: str, external_id: str) -> Event | None:
        row = self._db.execute(
            "SELECT data FROM events WHERE channel = ? AND external_id = ?",
            (channel, external_id),
        ).fetchone()
        return Event.model_validate_json(row["data"]) if row else None

    def get_event(self, event_id: str) -> Event | None:
        row = self._db.execute(
            "SELECT data FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return Event.model_validate_json(row["data"]) if row else None

    def save_event(self, event: Event) -> None:
        ts = (event.ts or datetime.now(timezone.utc)).isoformat()
        self._db.execute(
            "INSERT OR REPLACE INTO events (id, channel, external_id, lead_id, ts, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.channel.value,
                event.external_id,
                event.lead_id,
                ts,
                event.model_dump_json(),
            ),
        )
        self._db.commit()

    def list_events(
        self, lead_id: str | None = None, limit: int = 200
    ) -> list[Event]:
        if lead_id:
            rows = self._db.execute(
                "SELECT data FROM events WHERE lead_id = ? ORDER BY ts DESC LIMIT ?",
                (lead_id, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT data FROM events ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Event.model_validate_json(r["data"]) for r in rows]

    # --- settings ---

    def list_knowledge(self) -> list[KnowledgeBase]:
        rows = self._db.execute("SELECT data FROM knowledge ORDER BY id").fetchall()
        return [KnowledgeBase.model_validate_json(row["data"]) for row in rows]

    def get_knowledge(self, id: str) -> KnowledgeBase | None:
        row = self._db.execute("SELECT data FROM knowledge WHERE id=?", (id,)).fetchone()
        return KnowledgeBase.model_validate_json(row["data"]) if row else None

    def save_knowledge(self, knowledge: KnowledgeBase) -> None:
        self._db.execute("INSERT OR REPLACE INTO knowledge VALUES (?,?)", (knowledge.id, knowledge.model_dump_json()))
        self._db.commit()

    def delete_knowledge(self, id: str) -> None:
        self._db.execute("DELETE FROM knowledge WHERE id=?", (id,))
        self._db.commit()

    def get_settings(self) -> AppSettings:
        row = self._db.execute(
            "SELECT value FROM settings WHERE key = 'app'"
        ).fetchone()
        return AppSettings.model_validate(json.loads(row["value"])) if row else AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('app', ?)",
            (settings.model_dump_json(),),
        )
        self._db.commit()
