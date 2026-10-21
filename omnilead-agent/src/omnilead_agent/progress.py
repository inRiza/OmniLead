"""Observable execution events. Never collect model thoughts or raw model output."""

import asyncio
import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from threading import BoundedSemaphore, Event, Thread
from time import monotonic

_observer: ContextVar = ContextVar("agent_progress", default=None)
_cancellation: ContextVar = ContextVar("agent_cancellation", default=None)
_slots = BoundedSemaphore(8)
_MAX_EVENTS = 128
_JOB_TIMEOUT_SECONDS = 180
_HEARTBEAT_SECONDS = 10


class AnalysisCancelled(asyncio.CancelledError):
    """Control flow: cancellation must not trigger model/template fallback."""


def run_async(coroutine):
    """Propagate a disconnected stream to the active asynchronous SDK call."""
    cancellation = _cancellation.get()
    if cancellation is None:
        return asyncio.run(coroutine)

    async def supervised():
        task = asyncio.create_task(coroutine)
        try:
            while not task.done():
                if cancellation.is_set():
                    raise AnalysisCancelled()
                await asyncio.wait({task}, timeout=0.05)
            if cancellation.is_set():
                raise AnalysisCancelled()
            return task.result()
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return asyncio.run(supervised())


def emit(phase: str, label: str, **data) -> None:
    cancellation = _cancellation.get()
    if cancellation is not None and cancellation.is_set():
        raise AnalysisCancelled()
    observer = _observer.get()
    if observer is not None:
        observer(phase, label, data)


@contextmanager
def observe(sink=None, cancellation=None):
    records = []
    started = monotonic()

    def record(phase, label, data):
        if len(records) >= _MAX_EVENTS:
            return
        item = {"sequence": len(records) + 1, "phase": phase, "label": label,
                "at": datetime.now(timezone.utc).isoformat(),
                "elapsed_ms": round((monotonic() - started) * 1000), **data}
        records.append(item)
        if sink:
            sink(item)

    token = _observer.set(record)
    cancel_token = _cancellation.set(cancellation)
    try:
        yield records
    finally:
        _observer.reset(token)
        _cancellation.reset(cancel_token)


def run_observed(analyze, req, sink=None, cancellation=None):
    with observe(sink, cancellation) as records:
        result = analyze(req)
        result.trace.activity = records
        return result


async def stream_analysis(analyze, req):
    """NDJSON between agent and backend; no browser credentials or platform tokens."""
    slots = _slots
    if not slots.acquire(blocking=False):
        yield json.dumps({"type": "error", "message": "Agen sedang sibuk. Coba kembali sebentar lagi."}) + "\n"
        return
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=_MAX_EVENTS + 2)
    disconnected = Event()

    def deliver(item):
        if not disconnected.is_set():
            queue.put_nowait(item)

    def publish(item):
        if not disconnected.is_set():
            try:
                loop.call_soon_threadsafe(deliver, item)
            except RuntimeError:
                disconnected.set()

    def worker():
        try:
            result = run_observed(analyze, req, lambda item: publish({"type": "progress", "data": item}), disconnected)
            publish({"type": "result", "data": result.model_dump(mode="json")})
        except AnalysisCancelled:
            pass
        except Exception:
            # SDK exceptions may contain request URLs or credentials.
            publish({"type": "error", "message": "Analisis agen gagal. Coba proses ulang pesan."})
        finally:
            slots.release()

    try:
        Thread(target=worker, daemon=True).start()
    except RuntimeError:
        slots.release()
        yield json.dumps({"type": "error", "message": "Agen belum dapat memulai analisis."}) + "\n"
        return
    deadline = monotonic() + _JOB_TIMEOUT_SECONDS
    try:
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                yield json.dumps({"type": "error", "message": "Analisis melewati batas waktu."}) + "\n"
                break
            try:
                item = await asyncio.wait_for(queue.get(), timeout=min(_HEARTBEAT_SECONDS, remaining))
            except asyncio.TimeoutError:
                item = {"type": "heartbeat"}
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item["type"] in {"result", "error"}:
                break
    finally:
        disconnected.set()
