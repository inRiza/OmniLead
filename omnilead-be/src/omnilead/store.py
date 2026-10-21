"""Penyimpanan sederhana berbasis SQLite untuk aksi dan audit log.

Cukup untuk demo hackathon. Semua state penting (antrean persetujuan, audit)
ada di sini, jadi restart server tidak kehilangan data.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from omnilead.models import Action, ActionStatus, AuditEntry


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
                detail TEXT NOT NULL
            );
            """
        )
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

    def audit(self, event: str, detail: str, action_id: str | None = None) -> None:
        self._db.execute(
            "INSERT INTO audit (ts, action_id, event, detail) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), action_id, event, detail),
        )
        self._db.commit()

    def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        rows = self._db.execute(
            "SELECT id, ts, action_id, event, detail FROM audit "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            AuditEntry(
                id=r["id"],
                ts=datetime.fromisoformat(r["ts"]),
                action_id=r["action_id"],
                event=r["event"],
                detail=r["detail"],
            )
            for r in rows
        ]
