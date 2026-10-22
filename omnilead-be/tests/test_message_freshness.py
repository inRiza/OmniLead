from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from omnilead.message_freshness import browser_reply_hold, browser_timestamp

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


def test_relative_browser_times_are_not_import_times():
    assert browser_timestamp("11 hours ago", NOW) == NOW - timedelta(hours=11)
    assert browser_timestamp("5y", NOW) < NOW - timedelta(days=365)
    assert browser_timestamp("5/29/21", NOW).year == 2021


def test_old_and_undated_browser_messages_are_not_auto_replied():
    def event(time):
        return SimpleNamespace(meta={"source": "openclaw_text", "seen_at": time})
    assert browser_reply_hold(event("5y"), NOW)
    assert browser_reply_hold(event(""), NOW)
    assert not browser_reply_hold(event("10m"), NOW)
    assert not browser_reply_hold(SimpleNamespace(meta={"source": "meta_api"}), NOW)


def test_sqlite_background_writes_use_separate_connections(store):
    from concurrent.futures import ThreadPoolExecutor
    def write(i):
        store.audit("concurrency_check", str(i))
        return store._db
    with ThreadPoolExecutor(max_workers=6) as pool:
        connections = list(pool.map(write, range(36)))
    assert len({id(c) for c in connections}) > 1
    assert len([row for row in store.list_audit(100) if row.event == "concurrency_check"]) == 36
