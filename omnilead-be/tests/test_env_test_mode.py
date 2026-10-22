import pytest
from fastapi.testclient import TestClient

from omnilead import test_mode as tm
from omnilead.api import deps
from omnilead.config import Settings, get_settings
from omnilead.main import create_app
from omnilead.models import Channel
from tests.test_accounts_business import signup

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def app(tmp_path, monkeypatch, legacy_auth_mode):
    monkeypatch.setenv("OMNILEAD_AUTH_ENABLED", "true")
    monkeypatch.setenv("OMNILEAD_ACCOUNTS_DB_PATH", str(tmp_path / "accounts.db"))
    monkeypatch.setenv("OMNILEAD_DB_PATH", str(tmp_path / "crm.db"))
    monkeypatch.setenv("OMNILEAD_SECRETS_DIR", str(tmp_path / "secrets"))
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_USER_ID", "17841")
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_ACCESS_TOKEN", "env-token")
    monkeypatch.setenv("OMNILEAD_WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setenv("OMNILEAD_WHATSAPP_PHONE_NUMBER_ID", "")
    for cache in (get_settings, deps.get_accounts, deps.get_oauth, deps.store_for_workspace):
        cache.cache_clear()
    yield create_app()
    for cache in (get_settings, deps.get_accounts, deps.get_oauth, deps.store_for_workspace):
        cache.cache_clear()


def allow(monkeypatch, value):
    monkeypatch.setenv("OMNILEAD_TEST_MODE_ENABLED", "true" if value else "false")
    get_settings.cache_clear()


def test_env_accounts_and_statuses():
    s = Settings(instagram_user_id="1", instagram_access_token="t", whatsapp_phone_number_id="", whatsapp_access_token="")
    accounts = tm.env_accounts(s)
    assert accounts["instagram"]["configured"] and accounts["instagram"]["account_id"] == "1"
    assert not accounts["whatsapp"]["configured"] and accounts["whatsapp"]["account_id"] == ""
    statuses = {x["provider"]: x for x in tm.env_statuses(s)}
    assert statuses["instagram"]["status"] == "connected" and "pengujian" in statuses["instagram"]["label"]
    assert statuses["whatsapp"]["status"] == "disconnected"
    assert tm.env_bindings(s)["instagram"] == "1"


def test_test_mode_requires_server_permission(app, monkeypatch):
    allow(monkeypatch, False)
    client = TestClient(app)
    signup(client, "owner@example.com")
    assert client.get("/test-mode").json() == {"available": False, "enabled": False, "accounts": client.get("/test-mode").json()["accounts"]}
    assert client.put("/test-mode", json={"enabled": True}, headers=ORIGIN).status_code == 403


def test_test_mode_uses_env_account_without_oauth(app, monkeypatch):
    allow(monkeypatch, True)
    client = TestClient(app)
    user = signup(client, "owner@example.com")
    ws = user["workspace_id"]
    assert deps.registry_for_workspace(ws).get(Channel.INSTAGRAM).inner._token == ""

    r = client.put("/test-mode", json={"enabled": True}, headers=ORIGIN)
    assert r.status_code == 200 and r.json()["enabled"] is True
    assert next(a for a in r.json()["accounts"] if a["provider"] == "instagram")["configured"] is True

    connections = {c["provider"]: c for c in client.get("/connections").json()}
    assert connections["instagram"]["status"] == "connected" and connections["instagram"]["test_mode"]
    assert client.post("/connections/instagram/start", headers=ORIGIN).status_code == 409
    assert client.delete("/connections/instagram", headers=ORIGIN).status_code == 409

    registry = deps.registry_for_workspace(ws)
    ig = registry.get(Channel.INSTAGRAM)
    assert ig._token == "env-token" and ig._user_id == "17841"
    assert registry.account_ids["instagram"] == "17841"
    assert deps.account_bindings(ws)["instagram"] == "17841"
    events = [e.event for e in deps.store_for_workspace(ws).list_audit(limit=10)]
    assert "test_mode_on" in events

    assert client.put("/test-mode", json={"enabled": False}, headers=ORIGIN).json()["enabled"] is False
    assert deps.registry_for_workspace(ws).get(Channel.INSTAGRAM).inner._token == ""


def test_test_mode_is_off_when_server_permission_removed(app, monkeypatch):
    allow(monkeypatch, True)
    client = TestClient(app)
    ws = signup(client, "owner@example.com")["workspace_id"]
    client.put("/test-mode", json={"enabled": True}, headers=ORIGIN)
    allow(monkeypatch, False)
    assert client.get("/test-mode").json()["enabled"] is False
    assert deps.registry_for_workspace(ws).get(Channel.INSTAGRAM).inner._token == ""


def test_staff_cannot_toggle_test_mode(app, monkeypatch):
    allow(monkeypatch, True)
    owner = TestClient(app)
    ws = signup(owner, "owner@example.com")["workspace_id"]
    owner.post(f"/workspaces/{ws}/members", json={"email": "staff@example.com", "role": "staff"}, headers=ORIGIN)
    staff = TestClient(app)
    signup(staff, "staff@example.com", business="Lain")
    staff.post("/workspaces/select", json={"workspace_id": ws}, headers=ORIGIN)
    assert staff.put("/test-mode", json={"enabled": True}, headers=ORIGIN).status_code == 403
