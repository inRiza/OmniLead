"""Izin agen yang diatur pemilik, seperti mode izin pada coding assistant.

- hybrid: aksi berisiko rendah yang lolos Guard dijalankan otomatis. Membuka DM yang belum
  dibaca dan menerima permintaan pesan di browser menunggu izin pemilik.
- auto: akses penuh. Semua aksi yang lolos Guard dijalankan otomatis.

Pagar yang berlaku di semua mode: usulan dengan catatan Guard selain "pass", pesan yang
ditandai tinjauan manual, dan usulan gabung profil selalu menunggu manusia.
"""

import re
from typing import Literal

from omnilead.models import Action, ActionKind, Event

Mode = Literal["hybrid", "auto"]
BROWSER_GRANTS = ("read_unread", "accept_request")

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
    if action.kind == ActionKind.MERGE:
        return False
    if event is not None and event.status == "review":
        return False
    if action.guard and any(note.status != "pass" for note in action.guard):
        return False
    return mode == "auto" or is_low_risk(action, event)


def browser_grants(mode: Mode, allowed=()) -> set[str]:
    if mode == "auto":
        return set(BROWSER_GRANTS)
    return {g for g in allowed if g in BROWSER_GRANTS}
