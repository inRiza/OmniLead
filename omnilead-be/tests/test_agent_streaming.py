import json

import httpx
import pytest

from omnilead.agent_client import AgentClient, AgentUnavailable
from tests.test_ingest_api import CANNED


def test_older_agent_endpoint_falls_back_before_analysis_starts():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/v1/analyze/stream":
            return httpx.Response(404)
        return httpx.Response(200, json=CANNED)

    result = AgentClient("http://agent", transport=httpx.MockTransport(handler)).analyze_stream({}, lambda item: None)
    assert result.proposals and calls == ["/v1/analyze/stream", "/v1/analyze"]


def test_stream_progress_arrives_before_final_result():
    observed = []
    progress = {"phase": "drafting", "label": "Menyusun draf"}
    raw = "\n".join(json.dumps(item) for item in [
        {"type": "progress", "data": progress}, {"type": "heartbeat"}, {"type": "result", "data": CANNED}])
    client = AgentClient("http://agent", transport=httpx.MockTransport(lambda request: httpx.Response(200, text=raw)))
    assert client.analyze_stream({}, observed.append).proposals
    assert observed == [progress]


@pytest.mark.parametrize("raw", ['invalid-json', '{}', '{"type":"heartbeat"}',
    '{"type":"error","message":"private-model-secret"}', '{"type":"progress","data":{}}'])
def test_failed_stream_never_retries_or_exposes_provider_error(raw):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text=raw)

    with pytest.raises(AgentUnavailable) as error:
        AgentClient("http://agent", transport=httpx.MockTransport(handler)).analyze_stream({}, lambda item: None)
    assert "private-model-secret" not in str(error.value)
    assert calls == ["/v1/analyze/stream"]
