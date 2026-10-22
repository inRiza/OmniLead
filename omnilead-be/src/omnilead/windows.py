"""Jendela balasan kanal.

- WhatsApp: balasan teks bebas hanya dalam 24 jam sejak pesan masuk terakhir
  pelanggan. Di luar itu butuh template resmi.
- Instagram DM dan Facebook Messenger: 24 jam sejak pesan masuk terakhir.
- Private reply Instagram dan Facebook (pesan atas komentar): maksimal 7 hari
  sejak komentar dibuat dan hanya satu kali per komentar.
- Email dan kanal lain: tidak dibatasi.

Dicek oleh executor sebelum mengirim lewat API. Aksi di luar jendela tidak
pernah dikirim; hasilnya gagal dengan alasan "butuh template resmi".
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from omnilead.models import Action, ActionKind, ActionStatus, Channel, Event
from omnilead.store import Store

SERVICE_WINDOW = timedelta(hours=24)
PRIVATE_REPLY_WINDOW = timedelta(days=7)
PRIVATE_REPLY_CHANNELS = (Channel.INSTAGRAM, Channel.FACEBOOK)

SENT = (ActionStatus.EXECUTED, ActionStatus.EXECUTING)


@dataclass
class WindowResult:
    open: bool
    reason: str = ""


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _latest_inbound(events: list[Event], channel: Channel, dm_only: bool) -> Event | None:
    best: Event | None = None
    for e in events:
        if e.channel != channel or not e.ts:
            continue
        if dm_only and e.kind == "comment":
            continue
        if best is None or _aware(e.ts) > _aware(best.ts):  # type: ignore[operator]
            best = e
    return best


def check_window(
    store: Store, action: Action, now: datetime | None = None
) -> WindowResult:
    now = now or datetime.now(timezone.utc)
    if action.kind != ActionKind.SEND_MESSAGE or not action.lead_id:
        return WindowResult(True)
    if action.channel not in (Channel.WHATSAPP, Channel.INSTAGRAM, Channel.FACEBOOK):
        return WindowResult(True)

    events = store.list_events(lead_id=action.lead_id, limit=500)

    # Private reply Instagram/Facebook: dari komentar, 7 hari, sekali.
    if action.channel in PRIVATE_REPLY_CHANNELS and action.comment_ref:
        comment = next(
            (e for e in events if e.comment_ref == action.comment_ref and e.ts), None
        )
        if comment is None:
            return WindowResult(False, "Komentar asal tidak ditemukan; private reply tidak bisa dikirim")
        if now - _aware(comment.ts) > PRIVATE_REPLY_WINDOW:  # type: ignore[operator]
            return WindowResult(False, "Private reply lewat 7 hari sejak komentar. Butuh jalur lain")
        already = any(
            a.id != action.id
            and a.kind == ActionKind.SEND_MESSAGE
            and a.channel == action.channel
            and a.comment_ref == action.comment_ref
            and a.status in SENT
            for a in store.list_actions(lead_id=action.lead_id, kind=ActionKind.SEND_MESSAGE)
        )
        if already:
            return WindowResult(False, "Private reply untuk komentar ini sudah pernah dikirim (batas satu kali)")
        return WindowResult(True)

    last = _latest_inbound(events, action.channel, dm_only=True)
    if last is None:
        return WindowResult(False, "Belum ada pesan masuk dari pelanggan di kanal ini. Butuh template resmi")
    if now - _aware(last.ts) > SERVICE_WINDOW:  # type: ignore[operator]
        return WindowResult(False, "Jendela 24 jam tertutup. Butuh template resmi")
    return WindowResult(True)
