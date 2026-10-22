"""Izin agen yang diatur pemilik, seperti mode izin pada coding assistant.

- manual: setiap aksi menunggu persetujuan.
- hybrid: aksi berisiko rendah yang lolos Guard dijalankan otomatis.
- auto: semua aksi yang lolos Guard dijalankan otomatis.

Pagar yang berlaku di semua mode: usulan dengan catatan Guard selain "pass", pesan yang
ditandai tinjauan manual, dan usulan gabung profil selalu menunggu manusia.
"""

import re
from typing import Literal

from omnilead.models import Action, ActionKind, Event

Mode = Literal["manual", "hybrid", "auto"]

MONEY = re.compile(r"rp\s?\d|\d{1,3}(?:\.\d{3})+|\d+\s?%", re.IGNORECASE)
RISKY_INTENTS = {"komplain", "minta_penawaran"}


def is_low_risk(action: Action, event: Event | None) -> bool:
    if action.kind == ActionKind.CRM_UPDATE:
        return action.payload.get("stage") not in ("deal", "batal")
    if action.kind not in (ActionKind.SEND_MESSAGE, ActionKind.REPLY_COMMENT) or action.public:
        return False
    if MONEY.search(action.text):
        return False
    triage = (event.triage or {}) if event else {}
    if triage.get("urgency") == "tinggi" or RISKY_INTENTS & set(triage.get("intents", [])):
        return False
    return True


def auto_approvable(action: Action, event: Event | None, mode: Mode) -> bool:
    if mode == "manual" or action.kind == ActionKind.MERGE:
        return False
    if event is not None and event.status == "review":
        return False
    if not action.guard or any(note.status != "pass" for note in action.guard):
        return False
    return mode == "auto" or is_low_risk(action, event)
