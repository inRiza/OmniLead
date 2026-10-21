"""Akun demo untuk juri dibuat sekali saat server menyala dan berisi data demo."""

from fastapi.testclient import TestClient

from omnilead.api import deps
from omnilead.config import get_settings
from omnilead.main import create_app


def make_app(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("OMNILEAD_AUTH_ENABLED", "true")
    monkeypatch.setenv("OMNILEAD_ACCOUNTS_DB_PATH", str(tmp_path / "accounts.db"))
    monkeypatch.setenv("OMNILEAD_DB_PATH", str(tmp_path / "crm.db"))
    monkeypatch.setenv("OMNILEAD_SECRETS_DIR", str(tmp_path / "secrets"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    deps.store_for_workspace.cache_clear()
    return create_app()


def test_demo_account_is_created_seeded_and_can_log_in(tmp_path, monkeypatch, legacy_auth_mode):
    app = make_app(tmp_path, monkeypatch, OMNILEAD_DEMO_EMAIL="Juri@OmniLead.id", OMNILEAD_DEMO_PASSWORD="demo-juri-2026")
    with TestClient(app) as client:  # memicu startup
        login = client.post("/auth/login", json={"email": "juri@omnilead.id", "password": "demo-juri-2026"})
        assert login.status_code == 200, login.text
        leads = client.get("/leads").json()
        assert any(lead["name"] == "Ani" for lead in leads) and len(leads) >= 30
        # Agen memakai knowledge base bisnis: katalog demo harus terpasang di semua kanal.
        knowledge = client.get("/knowledge-bases").json()
        assert [k["id"] for k in knowledge] == ["demo-katalog"] and len(knowledge[0]["products"]) == 3
        channels = client.get("/agent/channel-settings").json()
        assert all(c["knowledge_base_ids"] == ["demo-katalog"] for c in channels.values())
        assert channels["email"]["tone"] == "professional"
    # Restart: akun yang sudah ada tidak dibuat ulang dan datanya tidak direset.
    with TestClient(make_app(tmp_path, monkeypatch, OMNILEAD_DEMO_EMAIL="juri@omnilead.id",
                             OMNILEAD_DEMO_PASSWORD="demo-juri-2026")) as client:
        assert client.post("/auth/login", json={"email": "juri@omnilead.id", "password": "demo-juri-2026"}).status_code == 200
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    deps.store_for_workspace.cache_clear()


def test_no_demo_account_without_env(tmp_path, monkeypatch, legacy_auth_mode):
    with TestClient(make_app(tmp_path, monkeypatch)) as client:
        assert client.post("/auth/login", json={"email": "juri@omnilead.id", "password": "x" * 12}).status_code in (400, 401)
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    deps.store_for_workspace.cache_clear()
