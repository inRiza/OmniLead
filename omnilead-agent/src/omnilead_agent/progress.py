"""Observable execution events. Never collect model thoughts or raw model output."""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic

_observer: ContextVar = ContextVar("agent_progress", default=None)


def emit(phase: str, label: str, **data) -> None:
    observer = _observer.get()
    if observer is not None:
        observer(phase, label, data)


@contextmanager
def observe(sink=None):
    records = []
    started = monotonic()

    def record(phase, label, data):
        item = {"sequence": len(records) + 1, "phase": phase, "label": label,
                "at": datetime.now(timezone.utc).isoformat(),
                "elapsed_ms": round((monotonic() - started) * 1000), **data}
        records.append(item)
        if sink:
            sink(item)

    token = _observer.set(record)
    try:
        yield records
    finally:
        _observer.reset(token)


def run_observed(analyze, req, sink=None):
    with observe(sink) as records:
        result = analyze(req)
        result.trace.activity = records
        return result


def stream_analysis(analyze, req):
    """NDJSON between agent and backend; no browser credentials or platform tokens."""
    queue = Queue()
    disconnected = Event()

    def publish(item):
        if not disconnected.is_set():
            queue.put(item)

    def worker():
        try:
            result = run_observed(analyze, req, lambda item: publish({"type": "progress", "data": item}))
            publish({"type": "result", "data": result.model_dump(mode="json")})
        except Exception:
            # SDK exceptions may contain request URLs or credentials.
            publish({"type": "error", "message": "Analisis agen gagal. Coba proses ulang pesan."})

    Thread(target=worker, daemon=True).start()
    try:
        while True:
            try:
                item = queue.get(timeout=10)
            except Empty:
                item = {"type": "heartbeat"}
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item["type"] in {"result", "error"}:
                break
    finally:
        disconnected.set()
