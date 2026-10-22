"""Penyimpanan SQLite untuk aksi, audit, lead, event, dan pengaturan.

Cukup untuk dev dan demo; restart server tidak kehilangan data. Antarmuka
metode di sini yang dipakai seluruh BE, sehingga adapter Firestore untuk
produksi cukup mengimplementasikan metode yang sama.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._connections = threading.local()
        self._init()
        self._db.execute("PRAGMA journal_mode=WAL")

    @property
    def _db(self):
        # Polling, chat tools, and analysis workers must never share a connection:
        # concurrent commits on one SQLite connection can raise SystemError.
        if not hasattr(self._connections, "db"):
            connection = sqlite3.connect(self._db_path, timeout=30, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            self._connections.db = connection
        return self._connections.db

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
            CREATE TABLE IF NOT EXISTS lead_identity (
                key TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                PRIMARY KEY (key, lead_id)
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
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
        action_cols = {r["name"] for r in self._db.execute("PRAGMA table_info(actions)")}
        if "lead_id" not in action_cols:
            self._db.execute("ALTER TABLE actions ADD COLUMN lead_id TEXT")
            self._db.execute("ALTER TABLE actions ADD COLUMN kind TEXT")
            for row in self._db.execute("SELECT id, data FROM actions").fetchall():
                data = json.loads(row["data"])
                self._db.execute("UPDATE actions SET lead_id = ?, kind = ? WHERE id = ?",
                                 (data.get("lead_id"), data.get("kind"), row["id"]))
        self._db.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_events_lead_ts ON events (lead_id, ts);
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
            CREATE INDEX IF NOT EXISTS idx_audit_rate ON audit (event, channel, ts);
            CREATE INDEX IF NOT EXISTS idx_audit_lead ON audit (lead_id);
            CREATE INDEX IF NOT EXISTS idx_actions_status ON actions (status, created_at);
            CREATE INDEX IF NOT EXISTS idx_actions_lead ON actions (lead_id);
            CREATE INDEX IF NOT EXISTS idx_actions_kind ON actions (kind);
            CREATE INDEX IF NOT EXISTS idx_identity_lead ON lead_identity (lead_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status, updated_at);
            """
        )
        indexed = self._db.execute("SELECT COUNT(*) AS n FROM lead_identity").fetchone()["n"]
        if not indexed:
            for row in self._db.execute("SELECT data FROM leads").fetchall():
                self._index_lead(Lead.model_validate_json(row["data"]), commit=False)
        self._db.commit()

    def reset(self) -> None:
        """Hapus semua data (dipakai skrip seed)."""
        for table in ("actions", "audit", "leads", "events", "settings", "knowledge", "lead_identity", "jobs", "agent_tasks", "chat_sessions"):
            self._db.execute(f"DELETE FROM {table}")
        self._db.commit()

    # --- actions ---

    def list_conversations(self) -> list[dict]:
        rows = [json.loads(row["data"]) for row in self._db.execute("SELECT data FROM chat_sessions").fetchall()]
        return sorted(rows, key=lambda c: c["updated_at"], reverse=True)

    def get_conversation(self, session_id: str) -> dict | None:
        row = self._db.execute("SELECT data FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def save_conversation(self, session: dict, expected_revision: int | None = None) -> bool:
        data = json.dumps(session, ensure_ascii=False)
        if expected_revision is None:
            cur = self._db.execute("INSERT OR IGNORE INTO chat_sessions VALUES (?, ?, ?)", (session["id"], session["revision"], data))
        else:
            cur = self._db.execute("UPDATE chat_sessions SET data = ?, revision = ? WHERE id = ? AND revision = ?",
                                   (data, session["revision"], session["id"], expected_revision))
        self._db.commit()
        return cur.rowcount == 1

    def list_agent_tasks(self) -> list[dict]:
        return [json.loads(row["data"]) for row in self._db.execute("SELECT data FROM agent_tasks ORDER BY rowid DESC").fetchall()]

    def get_agent_task(self, task_id: str) -> dict | None:
        row = self._db.execute("SELECT data FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def save_agent_task(self, task: dict, expected_revision: int | None = None) -> bool:
        data = json.dumps(task, ensure_ascii=False)
        if expected_revision is None:
            cur = self._db.execute("INSERT OR IGNORE INTO agent_tasks VALUES (?, ?, ?)", (task["id"], task["revision"], data))
        else:
            cur = self._db.execute("UPDATE agent_tasks SET data = ?, revision = ? WHERE id = ? AND revision = ?",
                                   (data, task["revision"], task["id"], expected_revision))
        self._db.commit()
        return cur.rowcount == 1

    def save_action(self, action: Action) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO actions (id, data, status, created_at, lead_id, kind) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                action.id,
                action.model_dump_json(),
                action.status.value,
                action.created_at.isoformat(),
                action.lead_id,
                action.kind.value,
            ),
        )
        self._db.commit()

    def get_action(self, action_id: str) -> Action | None:
        row = self._db.execute(
            "SELECT data FROM actions WHERE id = ?", (action_id,)
        ).fetchone()
        return Action.model_validate_json(row["data"]) if row else None

    def list_actions(
        self,
        status: ActionStatus | None = None,
        *,
        lead_id: str | None = None,
        kind: ActionKind | None = None,
        limit: int | None = None,
    ) -> list[Action]:
        where, args = [], []
        for col, value in (("status", status.value if status else None), ("lead_id", lead_id),
                           ("kind", kind.value if kind else None)):
            if value is not None:
                where.append(f"{col} = ?")
                args.append(value)
        sql = "SELECT data FROM actions"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            args.append(limit)
        rows = self._db.execute(sql, args).fetchall()
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
        self,
        limit: int = 100,
        channel: str | None = None,
        *,
        lead_id: str | None = None,
        event: str | None = None,
        actor: str | None = None,
        before_id: int | None = None,
    ) -> list[AuditEntry]:
        where, args = [], []
        for col, value in (("channel", channel), ("lead_id", lead_id), ("event", event), ("actor", actor)):
            if value is not None:
                where.append(f"{col} = ?")
                args.append(value)
        if before_id is not None:
            where.append("id < ?")
            args.append(before_id)
        sql = "SELECT * FROM audit"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._db.execute(sql + " ORDER BY id DESC LIMIT ?", (*args, limit)).fetchall()
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
        self._index_lead(lead, commit=False)
        self._db.commit()

    def _index_lead(self, lead: Lead, commit: bool = True) -> None:
        self._db.execute("DELETE FROM lead_identity WHERE lead_id = ?", (lead.id,))
        self._db.executemany("INSERT OR IGNORE INTO lead_identity (key, lead_id) VALUES (?, ?)",
                             [(k, lead.id) for k in identity_keys(lead)])
        if commit:
            self._db.commit()

    def find_leads_by_identity(self, key: str) -> list[Lead]:
        rows = self._db.execute(
            "SELECT l.data FROM lead_identity i JOIN leads l ON l.id = i.lead_id WHERE i.key = ?", (key,)
        ).fetchall()
        return [Lead.model_validate_json(r["data"]) for r in rows]

    def get_lead(self, lead_id: str) -> Lead | None:
        row = self._db.execute(
            "SELECT data FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()
        return Lead.model_validate_json(row["data"]) if row else None

    def delete_lead(self, lead_id: str) -> None:
        self._db.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        self._db.execute("DELETE FROM lead_identity WHERE lead_id = ?", (lead_id,))
        self._db.commit()

    def reassign_lead(self, old_id: str, new_id: str) -> None:
        """Pindahkan semua event dan aksi dari satu lead ke lead lain (saat merge)."""
        for event in self.list_events(lead_id=old_id, limit=10_000):
            event.lead_id = new_id
            self.save_event(event)
        for action in self.list_actions(lead_id=old_id):
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
        self, lead_id: str | None = None, limit: int = 200, *, before: datetime | None = None
    ) -> list[Event]:
        where, args = [], []
        if lead_id:
            where.append("lead_id = ?")
            args.append(lead_id)
        if before is not None:
            where.append("ts < ?")
            args.append(before.isoformat())
        sql = "SELECT data FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._db.execute(sql + " ORDER BY ts DESC LIMIT ?", (*args, limit)).fetchall()
        return [Event.model_validate_json(r["data"]) for r in rows]

    def enqueue_job(self, job_id: str, payload: dict) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._db.execute(
            "INSERT OR IGNORE INTO jobs (id, payload, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)",
            (job_id, json.dumps(payload), now, now),
        )
        self._db.commit()
        return cur.rowcount > 0

    def get_job(self, job_id: str) -> dict | None:
        row = self._db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return {**dict(row), "payload": json.loads(row["payload"])} if row else None

    def list_jobs(self, statuses: tuple[str, ...], older_than: timedelta | None = None, limit: int = 100) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - (older_than or timedelta(0))).isoformat()
        marks = ",".join("?" for _ in statuses)
        rows = self._db.execute(
            f"SELECT * FROM jobs WHERE status IN ({marks}) AND updated_at <= ? ORDER BY created_at LIMIT ?",
            (*statuses, cutoff, limit),
        ).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def update_job(self, job_id: str, status: str, error: str = "", attempt: bool = False) -> None:
        self._db.execute(
            "UPDATE jobs SET status = ?, error = ?, updated_at = ?, attempts = attempts + ? WHERE id = ?",
            (status, error[:500], datetime.now(timezone.utc).isoformat(), 1 if attempt else 0, job_id),
        )
        self._db.commit()

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
