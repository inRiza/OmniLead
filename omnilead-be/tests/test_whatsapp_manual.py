"""WhatsApp nomor uji: pemilik menempel Phone Number ID, WABA ID, dan token. Semua offline."""

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.oauth import OAuthError
from tests.test_accounts_oauth import app, oauth, signup  # noqa: F401 (fixture)

TOKEN = "EAAtesttoken-" + "x" * 20


def meta(seen: list, phones=({"id": "105000000000001", "display_phone_number": "+1 555 0100"},)):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"error": {"message": "Invalid OAuth access token", "code": 190}})
        if req.url.path.endswith("/205000000000009/phone_numbers"):
            return httpx.Response(200, json={"data": list(phones)})
        if req.url.path.endswith("/205000000000009/subscribed_apps"):
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404, json={"error": {"message": "not found"}})
    return handler


def test_manual_connection_verifies_number_subscribes_and_feeds_connector(app):  # noqa: F811
    seen = []
    service = oauth(app, meta(seen))
    service.whatsapp_manual("workspace", "105000000000001", "205000000000009", TOKEN)
    stored = service.accounts.connection("workspace", "whatsapp")
    assert stored["status"] == "connected" and stored["label"] == "+1 555 0100" and stored["source"] == "manual"
    assert any(r.method == "POST" and r.url.path.endswith("/205000000000009/subscribed_apps") for r in seen)
    cfg = service.connector_settings("workspace")
    assert cfg.whatsapp_phone_number_id == "105000000000001" and cfg.whatsapp_access_token == TOKEN
    assert service.accounts.asset_workspace("whatsapp", "105000000000001") == "workspace"


def test_manual_connection_rejects_wrong_number_bad_token_and_taken_number(app):  # noqa: F811
    service = oauth(app, meta([]))
    with pytest.raises(OAuthError, match="tidak ditemukan"):
        service.whatsapp_manual("workspace", "105000000000002", "205000000000009", TOKEN)
    with pytest.raises(OAuthError, match="tidak valid"):
        service.whatsapp_manual("workspace", "105000000000001", "205000000000009", "EAAwrong-" + "y" * 20)
    assert service.accounts.connection("workspace", "whatsapp") is None
    service.whatsapp_manual("workspace", "105000000000001", "205000000000009", TOKEN)
    with pytest.raises(OAuthError, match="bisnis lain"):
        service.whatsapp_manual("lain", "105000000000001", "205000000000009", TOKEN)


def test_manual_connection_requires_app_secret_and_route_validates_input(app):  # noqa: F811
    service = oauth(app, meta([]), meta_app_secret="")
    with pytest.raises(OAuthError, match="App Secret"):
        service.whatsapp_manual("workspace", "105000000000001", "205000000000009", TOKEN)
    assert next(s for s in service.statuses("workspace") if s["provider"] == "whatsapp")["manual"] is False

    assert next(s for s in oauth(app, meta([])).statuses("workspace") if s["provider"] == "whatsapp")["manual"] is True

    client = TestClient(app)
    signup(client)
    body = {"phone_number_id": "105000000000001", "waba_id": "205000000000009", "access_token": TOKEN}
    assert client.post("/connections/whatsapp/manual", json={**body, "phone_number_id": "abc"}).status_code == 422
    refused = client.post("/connections/whatsapp/manual", json=body)
    assert refused.status_code == 400 and "App Secret" in refused.json()["detail"]
    assert TOKEN not in refused.text
