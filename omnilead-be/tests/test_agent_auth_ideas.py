"""OIDC BE→agen, content ideas, dan penyaringan data."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from omnilead.agent_client import AgentClient, AgentUnavailable, google_id_token_provider
from omnilead.models import Channel, Event, Sender
from tests.test_platform import agent, client, wa  # noqa: F401  (fixture)

NOW = datetime.now(timezone.utc)


def test_oidc_token_attached_alongside_api_key():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(req.headers)
        return httpx.Response(200, json={"status": "ok"})

    ac = AgentClient("http://agent", api_key="k", transport=httpx.MockTransport(handler),
                     token_provider=lambda: "idtok")
    ac.health()
    assert seen["authorization"] == "Bearer idtok" and seen["x-api-key"] == "k"


def test_oidc_failure_becomes_agent_unavailable():
    def boom():
        raise RuntimeError("tidak ada ADC")

    ac = AgentClient("http://agent", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})),
                     token_provider=boom)
    with pytest.raises(AgentUnavailable, match="token identitas"):
        ac.health()


def test_google_token_provider_caches(monkeypatch):
    calls = []
    import google.oauth2.id_token as idt

    monkeypatch.setattr(idt, "fetch_id_token", lambda request, audience: calls.append(audience) or f"t{len(calls)}")
    provider = google_id_token_provider("https://agent.example")
    assert provider() == "t1" and provider() == "t1" and calls == ["https://agent.example"]


def test_content_ideas_sends_recent_messages_only(client, store, agent):  # noqa: F811
    for i, (text, ago) in enumerate([("hampers premium brp?", 1), ("hampers ready?", 2), ("pesan lama", 40)]):
        store.save_event(Event(id=f"e{i}", channel=Channel.INSTAGRAM, kind="comment", external_id=f"x{i}",
                               sender=Sender(handle="h"), text=text, ts=NOW - timedelta(days=ago)))
    sent = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/v1/content-ideas":
            sent.update(json.loads(req.content))
            return httpx.Response(200, json={"analyzed": 2, "ideas": [{"title": "Hampers"}]})
        return agent.handler(req)

    from omnilead.api import deps

    ac = AgentClient("http://agent", transport=httpx.MockTransport(handler))
    client.app.dependency_overrides[deps.get_agent_client] = lambda: ac
    r = client.get("/content-ideas", params={"days": 14})
    assert r.status_code == 200 and r.json()["ideas"][0]["title"] == "Hampers"
    assert sorted(m["text"] for m in sent["messages"]) == ["hampers premium brp?", "hampers ready?"]


def test_content_ideas_agent_down_is_502(client, agent):  # noqa: F811
    agent.down = True
    assert client.get("/content-ideas").status_code == 502
