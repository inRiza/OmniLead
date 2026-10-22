"""Offline security and lifecycle coverage. No real provider or Gemini calls."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.accounts import COOKIE, AccountStore, digest
from omnilead.api import deps
from omnilead.api.auth_routes import _attempts
from omnilead.config import Settings, get_settings
from omnilead.main import create_app
from omnilead.models import Channel, Lead, ProposedAction
from omnilead.oauth import OAuthError, OAuthService, SCOPES


@pytest.fixture
def app(tmp_path, monkeypatch, legacy_auth_mode):
    monkeypatch.setenv("OMNILEAD_AUTH_ENABLED", "true")
    monkeypatch.setenv("OMNILEAD_ACCOUNTS_DB_PATH", str(tmp_path / "accounts.db"))
    monkeypatch.setenv("OMNILEAD_DB_PATH", str(tmp_path / "crm.db"))
    monkeypatch.setenv("OMNILEAD_SECRETS_DIR", str(tmp_path / "secrets"))
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    deps.get_oauth.cache_clear()
    deps.store_for_workspace.cache_clear()
    _attempts.clear()
    app = create_app()
    yield app
    deps.get_accounts.cache_clear()
    deps.get_oauth.cache_clear()
    deps.store_for_workspace.cache_clear()
    get_settings.cache_clear()


def signup(client, email="owner@example.com"):
    response = client.post("/auth/register", json={
        "email": email, "password": "correct horse battery staple", "name": "Rina", "business": "Katering Rina",
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_sessions_rotate_logout_and_keys_do_not_bypass_login(app):
    client = TestClient(app)
    assert client.get("/leads", headers={"x-api-key": "anything"}).status_code == 401
    user = signup(client)
    first = client.cookies[COOKIE]
    assert "password" not in json.dumps(user)
    assert client.get("/auth/session").json()["user"] == user
    assert client.get("/leads").json() == []
    result = client.post("/auth/login", json={"email": user["email"], "password": "correct horse battery staple"})
    assert result.status_code == 200 and client.cookies[COOKIE] != first
    assert deps.get_accounts().user_for_session(first) is None
    assert "HttpOnly" in result.headers["set-cookie"] and "SameSite=lax" in result.headers["set-cookie"]
    current = client.cookies[COOKIE]
    assert client.post("/auth/logout").status_code == 200
    assert deps.get_accounts().user_for_session(current) is None
    assert client.get("/leads").status_code == 401


def test_tenant_reads_mutations_and_connection_metadata_are_isolated(app):
    a, b = TestClient(app), TestClient(app)
    alice, bob = signup(a, "a@example.com"), signup(b, "b@example.com")
    store = deps.store_for_workspace(alice["workspace_id"])
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    store.save_lead(Lead(id="private", name="Customer A", created_at=now, updated_at=now))
    assert a.get("/leads/private").status_code == 200
    assert b.get("/leads").json() == []
    assert b.get("/leads/private").status_code == 404
    a.post("/settings/pause", json={"paused": True})
    assert not b.get("/settings").json()["paused"]
    accounts = deps.get_accounts()
    accounts.save_connection(alice["workspace_id"], "instagram", {
        "access_token": "super-secret-token", "account_id": "a1", "label": "Alice", "status": "connected", "scopes": [],
    })
    assert "super-secret-token" not in a.get("/connections").text
    assert next(x for x in b.get("/connections").json() if x["provider"] == "instagram")["status"] == "disconnected"
    assert bob["workspace_id"] != alice["workspace_id"]


def test_csrf_and_bad_password(app):
    client = TestClient(app)
    signup(client)
    assert client.post("/auth/logout", headers={"origin": "https://evil.example"}).status_code == 403
    assert client.delete("/connections/instagram", headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert client.post("/auth/login", json={"email": "owner@example.com", "password": "wrong"}).status_code == 401


def test_state_is_bound_to_provider_browser_and_expires(app):
    accounts = deps.get_accounts()
    state = accounts.state("instagram", "workspace", "session")
    with pytest.raises(ValueError):
        accounts.consume_state(state, "gmail", "session")
    with pytest.raises(ValueError):
        accounts.consume_state(state, "instagram", "session")
    state = accounts.state("instagram", "workspace", "session")
    with pytest.raises(ValueError):
        accounts.consume_state(state, "instagram", "another-browser")
    state = accounts.state("instagram", "workspace", "session")
    data = accounts.get("state-" + digest(state))
    data["expires"] = time.time() - 1
    accounts.put("state-" + digest(state), data)
    with pytest.raises(ValueError):
        accounts.consume_state(state, "instagram", "session")


def test_credentials_encrypted_and_bound_to_workspace(app):
    accounts = deps.get_accounts()
    accounts.save_connection("a", "instagram", {"access_token": "secret-ig-token"})
    raw = accounts.get("connection-a-instagram")
    assert "secret-ig-token" not in json.dumps(raw)
    assert accounts.connection("a", "instagram")["access_token"] == "secret-ig-token"
    accounts.put("connection-b-instagram", raw)
    with pytest.raises(ValueError):
        accounts.connection("b", "instagram")


def oauth(app, handler, **kwargs):
    settings = get_settings().model_copy(update={
        "gmail_client_id": "google-id", "gmail_client_secret": "google-secret",
        "instagram_client_id": "ig-id", "instagram_client_secret": "ig-secret",
        "meta_app_id": "meta-id", "meta_app_secret": "meta-secret", "whatsapp_signup_config_id": "signup-id", **kwargs,
    })
    service = OAuthService(settings, deps.get_accounts(), httpx.Client(transport=httpx.MockTransport(handler)))
    deps.get_oauth.cache_clear()
    app.dependency_overrides[deps.get_oauth] = lambda: service
    return service


def test_instagram_code_long_token_webhook_connector_and_disconnect(app):
    seen = []
    def handler(req):
        seen.append(req)
        if req.url.host == "api.instagram.com":
            return httpx.Response(200, json={"access_token": "short", "user_id": "123", "permissions": SCOPES["instagram"]})
        if req.url.path == "/access_token":
            return httpx.Response(200, json={"access_token": "long-secret", "expires_in": 5184000})
        if req.url.path == "/me":
            return httpx.Response(200, json={"user_id": "123", "username": "rina"})
        return httpx.Response(200, json={"success": True})
    service = oauth(app, handler)
    state = service.start("instagram", "workspace", "browser")
    query = parse_qs(urlparse(state["url"]).query)
    assert "graph.instagram.com" not in state["url"] and "www.instagram.com" in state["url"]
    service.complete("instagram", "code", query["state"][0], "browser", "workspace")
    stored = service.accounts.connection("workspace", "instagram")
    assert stored["access_token"] == "long-secret" and stored["account_id"] == "123"
    assert any(r.url.path.endswith("/me/subscribed_apps") for r in seen)
    cfg = service.connector_settings("workspace")
    assert cfg.instagram_api_host == "https://graph.instagram.com"
    assert cfg.instagram_access_token == "long-secret"
    service.disconnect("workspace", "instagram")
    assert service.accounts.connection("workspace", "instagram") is None
    assert service.accounts.asset_workspace("instagram", "123") is None
    assert service.connector_settings("workspace").instagram_access_token == ""


def test_gmail_pkce_permissions_refresh_and_no_cross_account_refresh_reuse(app):
    deny_refresh = False
    def handler(req):
        if req.url.path == "/token":
            values = parse_qs(req.content.decode())
            if values["grant_type"] == ["refresh_token"]:
                return httpx.Response(400 if deny_refresh else 200, json={"error": "invalid_grant"} if deny_refresh else {"access_token": "fresh", "expires_in": 3600})
            assert "code_verifier" in values
            return httpx.Response(200, json={"access_token": "short", "refresh_token": "refresh-secret", "expires_in": 3600, "scope": " ".join(SCOPES["gmail"])})
        return httpx.Response(200, json={"emailAddress": "business@example.com"})
    service = oauth(app, handler)
    query = parse_qs(urlparse(service.start("gmail", "w", "s")["url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    service.complete("gmail", "code", query["state"][0], "s", "w")
    data = service.accounts.connection("w", "gmail")
    data["expires_at"] = time.time() - 1
    service.accounts.save_connection("w", "gmail", data)
    assert service.connection("w", "gmail")["access_token"] == "fresh"
    deny_refresh = True
    data["expires_at"] = time.time() - 1
    service.accounts.save_connection("w", "gmail", data)
    assert service.connection("w", "gmail")["status"] == "reconnect_required"
    assert service.connector_settings("w").gmail_refresh_token == ""


def test_removed_providers_do_not_offer_oauth(app):
    service = oauth(app, lambda r: httpx.Response(500))
    client = TestClient(app)
    signup(client)
    for provider in ("linkedin", "tiktok"):
        assert not service.ready(provider)
        with pytest.raises(OAuthError, match="tidak didukung"):
            service.start(provider, "w", "s")
        assert client.post(f"/connections/{provider}/start").status_code == 404
    assert {item["provider"] for item in client.get("/connections").json()} == {"instagram", "facebook", "gmail", "whatsapp"}


def test_asset_cannot_be_shared_between_businesses(app):
    service = oauth(app, lambda r: httpx.Response(200, json={"success": True}))
    connection = {"account_id": "123", "label": "@rina", "access_token": "secret", "expires_at": time.time() + 5184000}
    service.activate("a", "instagram", dict(connection))
    with pytest.raises(ValueError, match="bisnis lain"):
        service.activate("b", "instagram", dict(connection))
    assert service.accounts.connection("b", "instagram") is None


def test_whatsapp_discovers_number_and_does_not_trust_browser_assets(app):
    calls = []
    def handler(req):
        calls.append(req.url.path)
        if req.url.path.endswith("/oauth/access_token"):
            return httpx.Response(200, json={"access_token": "wa-secret"})
        if req.url.path.endswith("/debug_token"):
            return httpx.Response(200, json={"data": {"is_valid": True, "app_id": "meta-id", "scopes": SCOPES["whatsapp"],
                "granular_scopes": [{"scope": "whatsapp_business_management", "target_ids": ["777"]}]}})
        if req.url.path.endswith("/777/phone_numbers"):
            return httpx.Response(200, json={"data": [{"id": "888", "display_phone_number": "+62 812", "status": "CONNECTED"}]})
        return httpx.Response(200, json={"success": True})
    service = oauth(app, handler)
    start = service.start("whatsapp", "w", "s")
    result = service.whatsapp_exchange("w", "s", start["state"], "code")
    assert "wa-secret" not in json.dumps(result)
    assert result["accounts"][0]["id"] == "888"
    service.whatsapp_select("w", "s", result["selection"], "888", "")
    assert service.connector_settings("w").whatsapp_phone_number_id == "888"
    assert any(path.endswith("/777/subscribed_apps") for path in calls)
    assert not any(path.endswith("/register") for path in calls)


def test_webhook_routes_only_to_verified_recipient_workspace(app, monkeypatch):
    client = TestClient(app)
    user = signup(client)
    deps.get_accounts().claim_asset("instagram", "123", user["workspace_id"])
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-secret")
    get_settings.cache_clear()
    received = []
    class Ingest:
        def ingest(self, event):
            received.append(event)
    import omnilead.api.webhooks as webhooks
    monkeypatch.setattr(webhooks, "ingest_for_workspace", lambda workspace: Ingest())
    body = {"entry": [{"id": "123", "changes": [{"field": "comments", "value": {"id": "comment1", "text": "price?", "from": {"id": "customer"}}}]},
                      {"id": "other-business", "changes": [{"field": "comments", "value": {"id": "comment2", "text": "private"}}]}]}
    raw = json.dumps(body).encode()
    signature = "sha256=" + hmac.new(b"ig-secret", raw, hashlib.sha256).hexdigest()
    result = client.post("/webhooks/instagram", content=raw, headers={"x-hub-signature-256": signature})
    assert result.status_code == 200 and result.json()["accepted"] == 1
    assert len(received) == 1 and received[0].meta["business_account_id"] == "123"


def test_switching_account_cannot_send_draft_from_previous_account(app):
    from datetime import datetime, timezone
    from omnilead.approvals.queue import ApprovalQueue
    from omnilead.approvals.executor import Executor
    from omnilead.models import Event, Sender
    from tests.conftest import FakeConnector, FakeRegistry
    store = deps.store_for_workspace("w")
    queue = ApprovalQueue(store, account_bindings={"instagram": "old-account"})
    now = datetime.now(timezone.utc)
    store.save_event(Event(id="e", channel="instagram", kind="comment", external_id="c", sender=Sender(handle="customer"),
                           text="price?", ts=now, comment_ref="c", lead_id="l", meta={"business_account_id": "old-account"}))
    action = queue.propose(ProposedAction(channel=Channel.INSTAGRAM, kind="reply_comment", comment_ref="c", text="reply", event_id="e", lead_id="l"))
    connector = FakeConnector(Channel.INSTAGRAM, can_write=True)
    registry = FakeRegistry({Channel.INSTAGRAM: connector})
    registry.account_ids = {"instagram": "new-account"}
    result = Executor(registry, store).execute(queue.approve(action.id))
    assert result.status.value == "failed" and not connector.posted


def test_no_legacy_credentials_inherit_into_new_workspace(app):
    service = oauth(app, lambda r: httpx.Response(500), instagram_access_token="legacy-secret", gmail_refresh_token="legacy-refresh", whatsapp_access_token="legacy-wa")
    cfg = service.connector_settings("new-workspace")
    assert not cfg.instagram_access_token and not cfg.gmail_refresh_token and not cfg.whatsapp_access_token


def test_denied_callback_and_wrong_state_never_replace_existing_connection(app, monkeypatch):
    client = TestClient(app)
    user = signup(client)
    accounts = deps.get_accounts()
    old = {"access_token": "old-token", "account_id": "123", "label": "@rina", "status": "connected"}
    accounts.save_connection(user["workspace_id"], "instagram", old)
    state = accounts.state("instagram", user["workspace_id"], client.cookies[COOKIE])
    result = client.get("/auth/oauth/instagram/callback", params={"state": state, "error": "access_denied"}, follow_redirects=False)
    assert result.status_code == 303 and "cancelled" in result.headers["location"]
    assert accounts.connection(user["workspace_id"], "instagram") == old
    bad = client.get("/auth/oauth/instagram/callback", params={"state": "wrong", "code": "bad"}, follow_redirects=False)
    assert "failed" in bad.headers["location"] and "old-token" not in bad.text


def test_personal_signup_multiple_businesses_and_stale_tab_protection(app):
    client = TestClient(app)
    result = client.post("/auth/register", json={"email": "personal@example.com", "password": "a long password 2026", "name": "Personal"})
    assert result.status_code == 200
    original = result.json()["workspace_id"]
    assert result.json()["business"] == "Pribadi"
    created = client.post("/workspaces", json={"name": "Toko Kedua"})
    assert created.status_code == 200
    second = created.json()["id"]
    assert client.get("/auth/session").json()["user"]["workspace_id"] == second
    assert client.patch("/settings", json={"dry_run": True}, headers={"x-omnilead-workspace": original}).status_code == 409
    assert client.get("/settings").json()["dry_run"] is False
    client.patch("/settings", json={"dry_run": True})
    assert client.post("/workspaces/select", json={"workspace_id": original}).status_code == 200
    assert client.get("/settings").json()["dry_run"] is False
    assert set(deps.get_accounts().workspace_ids()) == {original, second}
    assert len(client.get("/workspaces").json()["workspaces"]) == 2


def test_workspace_membership_cannot_be_forged(app):
    a, b = TestClient(app), TestClient(app)
    alice, bob = signup(a, "workspace-a@example.com"), signup(b, "workspace-b@example.com")
    assert a.post("/workspaces/select", json={"workspace_id": bob["workspace_id"]}).status_code == 403
    assert a.get("/auth/session").json()["user"]["workspace_id"] == alice["workspace_id"]


def test_knowledge_crud_channel_assignment_and_tenant_isolation(app):
    a, b = TestClient(app), TestClient(app)
    signup(a, "knowledge-a@example.com")
    signup(b, "knowledge-b@example.com")
    document = a.post("/knowledge-bases", json={"name": "FAQ toko", "content": "# Jam buka\n\nKami buka pukul 09.00 sampai 17.00."}).json()
    assert document["name"] == "FAQ toko"
    assert b.get("/knowledge-bases").json() == []
    assert b.put(f"/knowledge-bases/{document['id']}", json={"name": "stolen", "content": "x"}).status_code == 404
    body = {"knowledge_base_ids": [document["id"]], "tone": "professional", "custom_tone": ""}
    assert b.patch("/agent/channel-settings/instagram", json=body).status_code == 422
    assert a.patch("/agent/channel-settings/instagram", json=body).status_code == 200
    settings = a.get("/agent/channel-settings").json()
    assert settings["instagram"]["tone"] == "professional" and settings["email"]["knowledge_base_ids"] == []
    assert a.patch("/agent/channel-settings/email", json={**body, "tone": "custom"}).status_code == 422
    assert a.delete(f"/knowledge-bases/{document['id']}").status_code == 200
    assert a.get("/agent/channel-settings").json()["instagram"]["knowledge_base_ids"] == []


def test_ingest_passes_only_channel_knowledge_and_tone_to_agent(app):
    from omnilead.agent_client import AgentClient
    from tests.test_ingest_api import CANNED
    client = TestClient(app)
    signup(client, "context@example.com")
    captured = []
    def handler(req):
        captured.append(json.loads(req.content))
        return httpx.Response(200, text=json.dumps({"type": "result", "data": CANNED}) + "\n",
                              headers={"content-type": "application/x-ndjson"})
    app.dependency_overrides[deps.get_agent_client] = lambda: AgentClient("http://agent", transport=httpx.MockTransport(handler))
    selected = client.post("/knowledge-bases", json={"name": "Jam buka", "content": "Kami buka jam 09.00.", "products": [{"name": "Kaos Basic", "unit_price": 75000, "unit": "pcs", "min_order": 1}]}).json()
    client.post("/knowledge-bases", json={"name": "Tidak dipilih", "content": "RAHASIA TIDAK UNTUK KANAL INI"})
    client.patch("/agent/channel-settings/instagram", json={"knowledge_base_ids": [selected["id"]], "tone": "professional"})
    event = {"channel": "instagram", "kind": "dm", "external_id": "test-context", "sender": {"handle": "customer"}, "text": "Jam buka?"}
    assert client.post("/events", json=event).status_code == 200
    context = captured[-1]["business_context"]
    assert context["tone"] == "professional" and "formal" in context["tone_instruction"]
    assert [d["name"] for d in context["documents"]] == ["Jam buka"]
    assert context["products"][0]["unit_price"] == 75000
    assert "RAHASIA" not in json.dumps(context)
    client.post("/events", json={**event, "channel": "email", "external_id": "email-context"})
    assert captured[-1]["business_context"]["documents"] == []
