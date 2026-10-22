import logging
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from omnilead.accounts import COOKIE, AccountStore, digest, hash_password
from omnilead.api import deps
from omnilead.config import get_settings
from omnilead.knowledge import build_context
from omnilead.main import create_app
from omnilead.store import Store

PASSWORD = "correct horse battery staple"


@pytest.fixture
def app(tmp_path, monkeypatch, legacy_auth_mode):
    monkeypatch.setenv("OMNILEAD_AUTH_ENABLED", "true")
    monkeypatch.setenv("OMNILEAD_ACCOUNTS_DB_PATH", str(tmp_path / "accounts.db"))
    monkeypatch.setenv("OMNILEAD_DB_PATH", str(tmp_path / "crm.db"))
    monkeypatch.setenv("OMNILEAD_SECRETS_DIR", str(tmp_path / "secrets"))
    monkeypatch.setenv("OMNILEAD_RESET_LINK_LOG", "true")
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    deps.get_oauth.cache_clear()
    deps.store_for_workspace.cache_clear()
    yield create_app()
    deps.get_accounts.cache_clear()
    deps.get_oauth.cache_clear()
    deps.store_for_workspace.cache_clear()
    get_settings.cache_clear()


def signup(client, email, business="Katering Rina", password=PASSWORD):
    response = client.post("/auth/register", json={"email": email, "password": password, "name": email.split("@")[0], "business": business})
    assert response.status_code == 200, response.text
    return response.json()


def session_user(client):
    return client.get("/auth/session").json()["user"]


def logged_token(caplog, param):
    for record in reversed(caplog.records):
        query = parse_qs(urlparse(record.getMessage().split(": ", 1)[1]).query)
        if param in query:
            return query[param][0]
    raise AssertionError("token tidak tercatat")


def test_free_plan_limits_owned_businesses_and_payload(app):
    client = TestClient(app)
    user = signup(client, "plan@example.com")
    assert user["plan"] == "free" and user["workspace_limit"] == 1 and user["owned_workspaces"] == 1
    assert user["email_verified"] is False and user["workspaces"][0]["role"] == "owner"
    blocked = client.post("/workspaces", json={"name": "Toko Kedua"})
    assert blocked.status_code == 409 and "Paket Free" in blocked.json()["detail"]
    deps.get_accounts().set_plan("plan@example.com", "pro")
    assert session_user(client)["workspace_limit"] == 3
    for name in ("Kedua", "Ketiga"):
        assert client.post("/workspaces", json={"name": name}).status_code == 200
    assert client.post("/workspaces", json={"name": "Keempat"}).status_code == 409
    assert session_user(client)["owned_workspaces"] == 3
    deps.get_accounts().set_plan("plan@example.com", "business")
    assert session_user(client)["workspace_limit"] == 10
    with pytest.raises(ValueError):
        deps.get_accounts().set_plan("plan@example.com", "gold")


def test_default_plan_setting_and_legacy_users_keep_existing_workspaces(app, monkeypatch):
    accounts = deps.get_accounts()
    accounts.put("user-" + digest("legacy@example.com"), {
        "id": "u1", "workspace_id": "a" * 32, "email": "legacy@example.com", "name": "Lama", "business": "Satu",
        "password": hash_password(PASSWORD), "workspaces": [{"id": "a" * 32, "name": "Satu"}, {"id": "b" * 32, "name": "Dua"}],
    })
    client = TestClient(app)
    assert client.post("/auth/login", json={"email": "legacy@example.com", "password": PASSWORD}).status_code == 200
    user = session_user(client)
    assert user["plan"] == "free" and user["owned_workspaces"] == 2 and user["email_verified"] is True
    assert client.post("/workspaces/select", json={"workspace_id": "b" * 32}).status_code == 200
    assert client.get("/workspaces/" + "b" * 32).json()["role"] == "owner"
    assert client.post("/workspaces", json={"name": "Tiga"}).status_code == 409
    monkeypatch.setenv("OMNILEAD_DEFAULT_PLAN", "business")
    get_settings.cache_clear()
    deps.get_accounts.cache_clear()
    assert session_user(client)["workspace_limit"] == 10
    assert client.post("/workspaces", json={"name": "Tiga"}).status_code == 200


def test_business_profile_crud_and_knowledge_context(app, tmp_path):
    client = TestClient(app)
    owner = signup(client, "profile@example.com")
    deps.get_accounts().set_plan(owner["email"], "pro")
    profile = {"category": "Katering", "description": "Nasi box rumahan", "service_area": "Jakarta Selatan", "hours": "08.00 sampai 17.00"}
    created = client.post("/workspaces", json={"name": "Dapur Dua", "profile": profile})
    assert created.status_code == 200 and created.json()["profile"] == profile
    workspace = created.json()["id"]
    detail = client.get(f"/workspaces/{workspace}").json()
    assert detail == {"id": workspace, "name": "Dapur Dua", "role": "owner", "profile": profile}
    patched = client.patch(f"/workspaces/{workspace}", json={"profile": {"hours": "24 jam"}})
    assert patched.status_code == 200 and patched.json()["profile"] == {**profile, "hours": "24 jam"}
    assert client.patch(f"/workspaces/{workspace}", json={"profile": {"category": "x" * 61}}).status_code == 422
    assert client.patch(f"/workspaces/{workspace}", json={"profile": {"unknown": "x"}}).status_code == 422
    first = client.get(f"/workspaces/{owner['workspace_id']}").json()
    assert first["profile"] == {} and first["name"] == "Katering Rina"
    stranger = TestClient(app)
    signup(stranger, "stranger@example.com")
    assert stranger.get(f"/workspaces/{workspace}").status_code == 404
    assert stranger.patch(f"/workspaces/{workspace}", json={"name": "Curian"}).status_code == 404
    stored = deps.get_accounts().workspace_profile(workspace)
    context = build_context(Store(tmp_path / "ctx.db"), "instagram", "jam buka?", profile=stored)
    document = context["documents"][0]
    assert document["name"] == "Profil bisnis" and "Jam operasional: 24 jam" in document["content"]
    assert "Area layanan: Jakarta Selatan" in document["content"]
    assert context["business_profile"]["category"] == "Katering"
    plain = build_context(Store(tmp_path / "ctx.db"), "instagram", "jam buka?")
    assert plain["documents"] == [] and plain["business_profile"] is None
    assert build_context(Store(tmp_path / "ctx.db"), "instagram", "x", profile={"category": " "})["documents"] == []


def test_rename_keeps_business_in_sync_for_owner_and_members(app):
    owner, member = TestClient(app), TestClient(app)
    alice = signup(owner, "rename-a@example.com")
    signup(member, "rename-b@example.com", business="Toko Bob")
    workspace = alice["workspace_id"]
    assert owner.post(f"/workspaces/{workspace}/members", json={"email": "rename-b@example.com", "role": "admin"}).status_code == 200
    assert owner.patch(f"/workspaces/{workspace}", json={"name": "  Katering Baru "}).json()["name"] == "Katering Baru"
    assert session_user(owner)["business"] == "Katering Baru"
    assert deps.get_accounts().get("user-" + digest("rename-a@example.com"))["business"] == "Katering Baru"
    assert any(w["name"] == "Katering Baru" and w["role"] == "admin" for w in member.get("/workspaces").json()["workspaces"])
    assert member.patch(f"/workspaces/{workspace}", json={"name": "Oleh Admin"}).status_code == 200
    assert session_user(owner)["business"] == "Oleh Admin"
    assert owner.patch(f"/workspaces/{workspace}", json={"name": ""}).status_code == 422
    assert owner.patch("/auth/profile", json={"name": "Rina", "business": "Lewat Profil"}).status_code == 200
    assert any(w["name"] == "Lewat Profil" for w in member.get("/workspaces").json()["workspaces"])


def test_archive_workspace_rules_channels_and_session_switch(app, tmp_path):
    owner, member = TestClient(app), TestClient(app)
    alice = signup(owner, "archive-a@example.com")
    signup(member, "archive-b@example.com", business="Toko Bob")
    accounts = deps.get_accounts()
    first = alice["workspace_id"]
    assert owner.delete(f"/workspaces/{first}").status_code == 409
    accounts.set_plan(alice["email"], "pro")
    second = owner.post("/workspaces", json={"name": "Cabang"}).json()["id"]
    owner.post(f"/workspaces/{second}/members", json={"email": "archive-b@example.com", "role": "admin"})
    owner.post(f"/workspaces/{second}/members", json={"email": "pending@example.com", "role": "staff"})
    assert member.post("/workspaces/select", json={"workspace_id": second}).status_code == 200
    assert member.delete(f"/workspaces/{second}").status_code == 403
    accounts.save_connection(second, "instagram", {"account_id": "777", "access_token": "secret-token"})
    accounts.claim_asset("instagram", "777", second)
    store = deps.store_for_workspace(second)
    from datetime import datetime, timezone
    from omnilead.models import Lead
    now = datetime.now(timezone.utc)
    store.save_lead(Lead(id="keep", name="Pelanggan", created_at=now, updated_at=now))
    assert session_user(owner)["workspace_id"] == second
    result = owner.delete(f"/workspaces/{second}")
    assert result.status_code == 200 and result.json()["active"] == first
    assert session_user(owner)["workspace_id"] == first
    assert accounts.connection(second, "instagram") is None
    assert accounts.asset_workspace("instagram", "777") is None
    assert second not in {w["id"] for w in session_user(member)["workspaces"]}
    assert session_user(member)["workspace_id"] != second
    assert member.get(f"/workspaces/{second}").status_code == 404
    assert second not in accounts.workspace_ids()
    assert accounts.get("invite-" + digest("pending@example.com")) is None
    assert (Path(get_settings().db_path).parent / "workspaces" / f"{second}.db").exists()
    assert deps.store_for_workspace(second).get_lead("keep") is not None
    assert owner.delete(f"/workspaces/{second}").status_code == 404
    assert session_user(owner)["owned_workspaces"] == 1


def test_invite_existing_user_roles_and_enforcement(app):
    owner, member, other = TestClient(app), TestClient(app), TestClient(app)
    alice = signup(owner, "team-a@example.com")
    bob = signup(member, "team-b@example.com", business="Toko Bob")
    signup(other, "team-c@example.com", business="Toko Cici")
    workspace = alice["workspace_id"]
    invited = owner.post(f"/workspaces/{workspace}/members", json={"email": "Team-B@Example.com", "role": "staff"})
    assert invited.status_code == 200 and invited.json()["accepted"] is True and invited.json()["role"] == "staff"
    assert owner.post(f"/workspaces/{workspace}/members", json={"email": "team-b@example.com", "role": "staff"}).status_code == 409
    assert owner.post(f"/workspaces/{workspace}/members", json={"email": "team-c@example.com", "role": "owner"}).status_code == 422
    entry = next(w for w in session_user(member)["workspaces"] if w["id"] == workspace)
    assert entry == {"id": workspace, "name": "Katering Rina", "role": "staff"}
    assert session_user(member)["owned_workspaces"] == 1
    assert member.post("/workspaces/select", json={"workspace_id": workspace}).status_code == 200
    assert member.get("/leads").status_code == 200
    assert member.get(f"/workspaces/{workspace}/members").status_code == 200
    assert member.post("/connections/instagram/start").status_code == 403
    assert member.delete("/connections/instagram").status_code == 403
    assert member.patch(f"/workspaces/{workspace}", json={"name": "x"}).status_code == 403
    assert member.patch("/auth/profile", json={"name": "Bob", "business": "Ganti"}).status_code == 403
    assert member.patch("/auth/profile", json={"name": "Bob Baru", "business": "Katering Rina"}).status_code == 200
    assert member.post(f"/workspaces/{workspace}/members", json={"email": "team-c@example.com", "role": "staff"}).status_code == 403
    assert member.delete(f"/workspaces/{workspace}").status_code == 403
    assert deps.get_accounts().role_for("team-b@example.com", workspace) == "staff"
    assert owner.patch(f"/workspaces/{workspace}/members/team-b@example.com", json={"role": "admin"}).status_code == 200
    assert next(w for w in session_user(member)["workspaces"] if w["id"] == workspace)["role"] == "admin"
    assert member.post(f"/workspaces/{workspace}/members", json={"email": "team-c@example.com", "role": "staff"}).status_code == 200
    assert member.patch(f"/workspaces/{workspace}/members/team-c@example.com", json={"role": "admin"}).status_code == 403
    assert owner.patch(f"/workspaces/{workspace}/members/team-a@example.com", json={"role": "staff"}).status_code == 409
    assert owner.patch(f"/workspaces/{workspace}/members/nobody@example.com", json={"role": "staff"}).status_code == 404
    assert member.delete(f"/workspaces/{workspace}/members/team-a@example.com").status_code == 409
    members = owner.get(f"/workspaces/{workspace}/members").json()["members"]
    assert [(m["email"], m["role"]) for m in members] == [("team-a@example.com", "owner"), ("team-b@example.com", "admin"), ("team-c@example.com", "staff")]
    assert members[1]["name"] == "Bob Baru"
    assert other.delete(f"/workspaces/{workspace}/members/team-b@example.com").status_code == 403
    assert other.delete(f"/workspaces/{workspace}/members/team-c@example.com").status_code == 200
    assert workspace not in {w["id"] for w in session_user(other)["workspaces"]}
    assert other.get(f"/workspaces/{workspace}").status_code == 404
    assert owner.delete(f"/workspaces/{workspace}/members/team-b@example.com").status_code == 200
    user = session_user(member)
    assert user["workspace_id"] == bob["workspace_id"] and workspace not in {w["id"] for w in user["workspaces"]}
    assert member.post("/workspaces/select", json={"workspace_id": workspace}).status_code == 403
    assert deps.get_accounts().role_for("team-b@example.com", workspace) is None


def test_invite_before_registration_attaches_on_signup(app):
    owner = TestClient(app)
    alice = signup(owner, "invite-a@example.com")
    workspace = alice["workspace_id"]
    pending = owner.post(f"/workspaces/{workspace}/members", json={"email": "later@example.com", "role": "admin"})
    assert pending.status_code == 200 and pending.json()["accepted"] is False
    assert deps.get_accounts().get("invite-" + digest("later@example.com"))["workspaces"] == [workspace]
    newcomer = TestClient(app)
    user = signup(newcomer, "later@example.com", business="Usaha Sendiri")
    assert {w["id"]: w["role"] for w in user["workspaces"]} == {user["workspace_id"]: "owner", workspace: "admin"}
    assert user["owned_workspaces"] == 1 and user["business"] == "Usaha Sendiri"
    assert deps.get_accounts().get("invite-" + digest("later@example.com")) is None
    assert next(m for m in owner.get(f"/workspaces/{workspace}/members").json()["members"] if m["email"] == "later@example.com")["accepted"] is True
    assert newcomer.post("/workspaces/select", json={"workspace_id": workspace}).status_code == 200
    assert newcomer.patch(f"/workspaces/{workspace}", json={"profile": {"category": "Katering"}}).status_code == 200
    owner.post(f"/workspaces/{workspace}/members", json={"email": "never@example.com", "role": "staff"})
    assert owner.delete(f"/workspaces/{workspace}/members/never@example.com").status_code == 200
    assert deps.get_accounts().get("invite-" + digest("never@example.com")) is None


def test_lazy_membership_for_existing_workspace(app):
    accounts = deps.get_accounts()
    accounts.put("user-" + digest("old@example.com"), {
        "id": "u2", "workspace_id": "c" * 32, "email": "old@example.com", "name": "Lama", "business": "Lama",
        "password": hash_password(PASSWORD), "workspaces": [{"id": "c" * 32, "name": "Lama"}],
    })
    assert accounts.get("workspace-" + "c" * 32) is None
    assert accounts.role_for("old@example.com", "c" * 32) == "owner"
    assert accounts.get("workspace-" + "c" * 32)["owner_email"] == "old@example.com"
    assert accounts.role_for("someone@example.com", "d" * 32) is None


def test_password_change_revokes_other_sessions(app):
    first, second = TestClient(app), TestClient(app)
    signup(first, "pw@example.com")
    assert second.post("/auth/login", json={"email": "pw@example.com", "password": PASSWORD}).status_code == 200
    assert first.post("/auth/password", json={"current_password": "wrong password!", "new_password": "another long password"}).status_code == 400
    assert first.post("/auth/password", json={"current_password": PASSWORD, "new_password": "short"}).status_code == 422
    assert first.post("/auth/password", json={"current_password": PASSWORD, "new_password": "another long password"}, headers={"origin": "https://evil.example"}).status_code == 403
    assert first.post("/auth/password", json={"current_password": PASSWORD, "new_password": "another long password"}).status_code == 200
    assert first.get("/leads").status_code == 200
    assert second.get("/leads").status_code == 401
    assert second.post("/auth/login", json={"email": "pw@example.com", "password": PASSWORD}).status_code == 401
    assert second.post("/auth/login", json={"email": "pw@example.com", "password": "another long password"}).status_code == 200


def test_revoke_other_sessions(app):
    first, second = TestClient(app), TestClient(app)
    signup(first, "revoke@example.com")
    second.post("/auth/login", json={"email": "revoke@example.com", "password": PASSWORD})
    assert first.post("/auth/sessions/revoke").status_code == 200
    assert first.get("/leads").status_code == 200
    assert second.get("/leads").status_code == 401
    assert deps.get_accounts().get("session-" + digest(second.cookies[COOKIE])) is None


def test_password_reset_single_use_expiry_and_no_enumeration(app, caplog):
    client = TestClient(app)
    signup(client, "reset@example.com")
    other = TestClient(app)
    other.post("/auth/login", json={"email": "reset@example.com", "password": PASSWORD})
    caplog.set_level(logging.WARNING, logger="omnilead.api.auth_routes")
    unknown = client.post("/auth/password/reset-request", json={"email": "ghost@example.com"})
    assert unknown.status_code == 202 and not caplog.records
    known = client.post("/auth/password/reset-request", json={"email": "Reset@Example.com"})
    assert known.status_code == 202 and known.json() == unknown.json()
    assert "http://localhost:3000/login?reset=" in caplog.records[-1].getMessage()
    token = logged_token(caplog, "reset")
    assert client.post("/auth/password/reset", json={"token": token, "new_password": "short"}).status_code == 422
    assert client.post("/auth/password/reset", json={"token": token, "new_password": "a brand new password"}).status_code == 200
    assert client.post("/auth/password/reset", json={"token": token, "new_password": "a brand new password"}).status_code == 400
    assert client.get("/leads").status_code == 401 and other.get("/leads").status_code == 401
    assert client.post("/auth/login", json={"email": "reset@example.com", "password": "a brand new password"}).status_code == 200
    accounts = deps.get_accounts()
    expired = accounts.reset_token("reset@example.com")
    record = accounts.get("reset-" + digest(expired))
    accounts.put("reset-" + digest(expired), {**record, "expires": time.time() - 1})
    assert client.post("/auth/password/reset", json={"token": expired, "new_password": "yet another password"}).status_code == 400
    stale = accounts.reset_token("reset@example.com")
    assert record["expires"] - time.time() <= 1800
    client.post("/auth/password", json={"current_password": "a brand new password", "new_password": "changed in between"})
    assert client.post("/auth/password/reset", json={"token": stale, "new_password": "yet another password"}).status_code == 400


def test_reset_link_not_logged_without_setting(app, caplog, monkeypatch):
    monkeypatch.setenv("OMNILEAD_RESET_LINK_LOG", "false")
    get_settings.cache_clear()
    client = TestClient(app)
    signup(client, "quiet@example.com")
    caplog.set_level(logging.WARNING, logger="omnilead.api.auth_routes")
    assert client.post("/auth/password/reset-request", json={"email": "quiet@example.com"}).status_code == 202
    assert not caplog.records


def test_email_verification(app, caplog):
    client = TestClient(app)
    assert signup(client, "verify@example.com")["email_verified"] is False
    caplog.set_level(logging.WARNING, logger="omnilead.api.auth_routes")
    assert client.post("/auth/verify-email/request").json() == {"ok": True, "email_verified": False}
    token = logged_token(caplog, "verify")
    assert TestClient(app).post("/auth/verify-email", json={"token": token}).status_code == 200
    assert session_user(client)["email_verified"] is True
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400
    assert client.post("/auth/verify-email/request").json()["email_verified"] is True
    assert TestClient(app).post("/auth/verify-email/request").status_code == 401


def test_delete_account_archives_solo_workspaces_and_transfers_shared(app):
    owner, admin, staff = TestClient(app), TestClient(app), TestClient(app)
    alice = signup(owner, "delete-a@example.com")
    signup(admin, "delete-b@example.com", business="Toko Bob")
    signup(staff, "delete-c@example.com", business="Toko Cici")
    accounts = deps.get_accounts()
    accounts.set_plan(alice["email"], "pro")
    shared = alice["workspace_id"]
    solo = owner.post("/workspaces", json={"name": "Sendiri"}).json()["id"]
    owner.post(f"/workspaces/{shared}/members", json={"email": "delete-c@example.com", "role": "staff"})
    owner.post(f"/workspaces/{shared}/members", json={"email": "delete-b@example.com", "role": "admin"})
    cici_space = session_user(staff)["workspace_id"]
    staff.post(f"/workspaces/{cici_space}/members", json={"email": "delete-a@example.com", "role": "staff"})
    accounts.save_connection(solo, "gmail", {"account_id": "solo@example.com", "access_token": "t"})
    accounts.claim_asset("gmail", "solo@example.com", solo)
    second = TestClient(app)
    second.post("/auth/login", json={"email": "delete-a@example.com", "password": PASSWORD})
    assert owner.request("DELETE", "/auth/account", json={"password": "wrong password!"}).status_code == 400
    result = owner.request("DELETE", "/auth/account", json={"password": PASSWORD})
    assert result.status_code == 200 and "Max-Age=0" in result.headers["set-cookie"]
    assert accounts.get("user-" + digest("delete-a@example.com")) is None
    assert owner.get("/leads").status_code == 401 and second.get("/leads").status_code == 401
    assert accounts.connection(solo, "gmail") is None and accounts.asset_workspace("gmail", "solo@example.com") is None
    assert accounts.get("workspace-" + solo)["archived"] is True
    record = accounts.get("workspace-" + shared)
    assert record["owner_email"] == "delete-b@example.com"
    assert [m["email"] for m in record["members"]] == ["delete-c@example.com", "delete-b@example.com"]
    assert next(w for w in session_user(admin)["workspaces"] if w["id"] == shared)["role"] == "owner"
    assert admin.get(f"/workspaces/{shared}").json()["role"] == "owner"
    assert all(m["email"] != "delete-a@example.com" for m in accounts.get("workspace-" + cici_space)["members"])
    assert admin.post("/auth/login", json={"email": "delete-a@example.com", "password": PASSWORD}).status_code == 401
    reborn = TestClient(app)
    reborn.cookies.set(COOKIE, second.cookies[COOKIE])
    signup(TestClient(app), "delete-a@example.com")
    assert reborn.get("/leads").status_code == 401


def test_sliding_session_renewal(app):
    client = TestClient(app)
    signup(client, "slide@example.com")
    accounts = deps.get_accounts()
    key = "session-" + digest(client.cookies[COOKIE])
    lifetime = get_settings().session_days * 86400
    fresh = accounts.get(key)["expires"]
    client.get("/leads")
    assert accounts.get(key)["expires"] == fresh
    accounts.put(key, {**accounts.get(key), "expires": time.time() + 86400})
    response = client.get("/auth/session")
    renewed = accounts.get(key)["expires"]
    assert renewed > time.time() + lifetime - 60
    max_age = int(re.search(r"Max-Age=(\d+)", response.headers["set-cookie"]).group(1))
    assert max_age > lifetime - 60
    accounts.put(key, {**accounts.get(key), "expires": time.time() - 1})
    assert client.get("/leads").status_code == 401
    assert accounts.get(key) is None


def test_persistent_login_rate_limit(app):
    client = TestClient(app)
    for _ in range(8):
        assert client.post("/auth/login", json={"email": "limit@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json={"email": "limit@example.com", "password": "wrong"}).status_code == 429
    deps.get_accounts.cache_clear()
    fresh = AccountStore(get_settings())
    assert fresh.get("ratelimit-" + digest("email:" + digest("limit@example.com")))["hits"]
    assert client.post("/auth/login", json={"email": "limit@example.com", "password": "wrong"}).status_code == 429
    key = "ratelimit-" + digest("email:" + digest("limit@example.com"))
    fresh.put(key, {"hits": [time.time() - 61] * 8, "expires": time.time()})
    assert client.post("/auth/login", json={"email": "limit@example.com", "password": "wrong"}).status_code == 401
    assert len(fresh.get(key)["hits"]) == 1
    for index in range(30):
        client.post("/auth/login", json={"email": f"spray{index}@example.com", "password": "wrong"})
    assert client.post("/auth/login", json={"email": "fresh@example.com", "password": "wrong"}).status_code == 429
