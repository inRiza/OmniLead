"""Execution streams, isolation and cancellation without LLM or platform traffic."""

import asyncio
import json
from threading import BoundedSemaphore, Event

from omnilead_agent import progress
from omnilead_agent.schemas import AnalyzeResponse, Trace, TriageResult


def result(id="sample"):
    return AnalyzeResponse(event_id=id, triage=TriageResult(intents=["pertanyaan_umum"],
        urgency="rendah", urgency_reason="Pertanyaan biasa", sentiment="netral"), trace=Trace(goal="Uji"))


def test_stream_delivers_progress_then_result_and_keeps_history():
    def analyze(req):
        progress.emit("tool", "Tool selesai", tool="get_timeline", input={}, result="Profil baru")
        return result()

    async def collect():
        return [json.loads(line) async for line in progress.stream_analysis(analyze, None)]

    packets = asyncio.run(collect())
    assert [p["type"] for p in packets] == ["progress", "result"]
    assert packets[1]["data"]["trace"]["activity"] == [packets[0]["data"]]


def test_disconnect_cancels_the_active_async_model_call():
    stopped = Event()

    async def model_call():
        try:
            progress.emit("drafting", "Model sedang berjalan")
            await asyncio.sleep(30)
        finally:
            stopped.set()

    def analyze(req):
        progress.run_async(model_call())
        return result()

    async def run():
        stream = progress.stream_analysis(analyze, None)
        first = json.loads(await anext(stream))
        assert first["type"] == "progress"
        await stream.aclose()
        assert await asyncio.to_thread(stopped.wait, 2)

    asyncio.run(run())


def test_job_deadline_cancels_sdk_and_returns_error(monkeypatch):
    stopped = Event()
    monkeypatch.setattr(progress, "_JOB_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(progress, "_HEARTBEAT_SECONDS", 0.02)

    async def model_call():
        try:
            await asyncio.sleep(30)
        finally:
            stopped.set()

    def analyze(req):
        progress.run_async(model_call())
        return result()

    async def run():
        packets = [json.loads(line) async for line in progress.stream_analysis(analyze, None)]
        assert packets[-1]["type"] == "error"
        assert await asyncio.to_thread(stopped.wait, 2)

    asyncio.run(run())


def test_stream_capacity_is_bounded(monkeypatch):
    stopped = Event()
    monkeypatch.setattr(progress, "_slots", BoundedSemaphore(1))

    async def model_call():
        try:
            progress.emit("drafting", "Model sedang berjalan")
            await asyncio.sleep(30)
        finally:
            stopped.set()

    def analyze(req):
        progress.run_async(model_call())
        return result()

    async def run():
        first = progress.stream_analysis(analyze, None)
        await anext(first)
        second = [json.loads(line) async for line in progress.stream_analysis(analyze, None)]
        assert len(second) == 1 and second[0]["type"] == "error"
        await first.aclose()
        assert await asyncio.to_thread(stopped.wait, 2)

    asyncio.run(run())


def test_concurrent_requests_do_not_share_activity():
    def analyze(req):
        progress.emit("plan", "Rencana " + req)
        return result(req)

    async def collect(id):
        return [json.loads(line) async for line in progress.stream_analysis(analyze, id)]

    async def run():
        a, b = await asyncio.gather(collect("business-a"), collect("business-b"))
        assert a[-1]["data"]["trace"]["activity"][0]["label"] == "Rencana business-a"
        assert b[-1]["data"]["trace"]["activity"][0]["label"] == "Rencana business-b"

    asyncio.run(run())


def test_exception_text_is_not_exposed():
    def analyze(req):
        raise ValueError("private-secret-must-not-appear")

    async def collect():
        return "".join([line async for line in progress.stream_analysis(analyze, None)])

    raw = asyncio.run(collect())
    assert "private-secret" not in raw and json.loads(raw)["type"] == "error"


def test_progress_memory_is_bounded():
    def analyze(req):
        for _ in range(1000):
            progress.emit("tool", "Tool selesai")
        return result()

    async def collect():
        return [json.loads(line) async for line in progress.stream_analysis(analyze, None)]

    packets = asyncio.run(collect())
    assert len(packets) == progress._MAX_EVENTS + 1
    assert packets[-1]["type"] == "result"


def test_http_stream_endpoint_authentication_and_pipeline(monkeypatch):
    from fastapi.testclient import TestClient
    from omnilead_agent.main import create_app

    monkeypatch.setenv("OMNILEAD_AGENT_ENGINE", "rule")
    monkeypatch.setenv("OMNILEAD_AGENT_API_KEY", "test-service-key")
    client = TestClient(create_app())
    payload = {"event": {"id": "http-stream", "channel": "instagram", "kind": "dm",
                        "sender": {"handle": "customer"}, "text": "Jam buka?"}}
    assert client.post("/v1/analyze/stream", json=payload).status_code == 401
    response = client.post("/v1/analyze/stream", json=payload, headers={"x-api-key": "test-service-key"})
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/x-ndjson")
    packets = [json.loads(line) for line in response.text.splitlines()]
    assert packets[-1]["type"] == "result"
    assert packets[-1]["data"]["trace"]["activity"]
    assert packets[-1]["data"]["event_id"] == "http-stream"
