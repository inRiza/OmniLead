"""Browser imports must not turn an old/undated DM into a new auto-reply target."""
import re
from datetime import datetime, timedelta, timezone


def browser_timestamp(label: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    text = label.strip().lower()
    if text in ("now", "just now", "baru saja", "sekarang"):
        return now
    match = re.fullmatch(r"(\d+)\s*(s|sec|secs|second|seconds|detik|m|min|mins|minute|minutes|mnt|menit|h|hr|hrs|hour|hours|jam|d|day|days|hari|w|wk|week|weeks|minggu|mo|month|months|bulan|y|yr|year|years|tahun)(?:\s+(?:ago|lalu|yang lalu))?", text)
    if match:
        count, unit = int(match[1]), match[2]
        groups = [(60, {"m", "min", "mins", "minute", "minutes", "mnt", "menit"}),
                  (3600, {"h", "hr", "hrs", "hour", "hours", "jam"}),
                  (86400, {"d", "day", "days", "hari"}),
                  (604800, {"w", "wk", "week", "weeks", "minggu"}),
                  (2592000, {"mo", "month", "months", "bulan"}),
                  (31536000, {"y", "yr", "year", "years", "tahun"})]
        seconds = next((size for size, names in groups if unit in names), 1)
        try:
            return now - timedelta(seconds=count * seconds)
        except OverflowError:
            return datetime.min.replace(tzinfo=timezone.utc)
    try:
        date = datetime.fromisoformat(text.replace("z", "+00:00"))
        return date if date.tzinfo else date.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for pattern in ("%m/%d/%y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def browser_reply_hold(event, now: datetime | None = None) -> str:
    if not event or event.meta.get("source") != "openclaw_text":
        return ""
    now = now or datetime.now(timezone.utc)
    sent = browser_timestamp(str(event.meta.get("seen_at") or ""), now)
    if sent is None:
        return "Waktu pesan browser belum terverifikasi; tinjau manual sebelum membalas."
    if now - sent >= timedelta(hours=24) or sent > now + timedelta(minutes=5):
        return "Pesan lama di luar 24 jam; tidak dibalas otomatis."
    return ""
