import logging
import re
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from omnilead.accounts import COOKIE, MANAGERS, ROLES, digest, hash_password, password_matches
from omnilead.api.deps import current_user, get_accounts, get_oauth, store_for_workspace
from omnilead.config import get_settings
from omnilead.oauth import OAuthError, PROVIDERS
from omnilead.test_mode import env_accounts, env_statuses, test_mode_active

router = APIRouter(tags=["accounts"])
log = logging.getLogger(__name__)
_attempts: dict = {}


def check_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    settings = get_settings()
    allowed = {settings.frontend_url.rstrip("/"), *settings.cors_origins}
    if (origin and origin.rstrip("/") not in allowed) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Permintaan berasal dari situs lain")


def _rate_limit(request: Request, email: str) -> None:
    limits = {"ip:" + (request.client.host if request.client else "local"): 30, "email:" + digest(email.lower()): 8}
    if get_accounts().rate_limited(limits):
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Tunggu satu menit.")


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class Register(Login):
    name: str = Field(min_length=1, max_length=100)
    business: str = Field(default="Pribadi", min_length=1, max_length=100)


class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    business: str = Field(min_length=1, max_length=100)


def _email(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(status_code=422, detail="Alamat email tidak valid")
    return value


def public_user(user: dict) -> dict:
    accounts = get_accounts()
    return {**{key: user[key] for key in ("id", "workspace_id", "email", "name", "business")},
            "workspaces": accounts.spaces(user), "plan": accounts.plan(user),
            "workspace_limit": accounts.workspace_limit(user), "owned_workspaces": accounts.owned(user),
            "email_verified": user.get("email_verified", True)}


def _password(value: str) -> str:
    if len(value) < 12:
        raise HTTPException(status_code=422, detail="Gunakan kata sandi minimal 12 karakter")
    return value


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/", secure=get_settings().frontend_url.startswith("https://"), httponly=True, samesite="lax")


def _role(user: dict, workspace: str, allowed: tuple = ROLES) -> str:
    member = any(w["id"] == workspace for w in user["workspaces"])
    role = get_accounts().role_for(user["email"], workspace) if member else None
    if not role:
        raise HTTPException(status_code=404, detail="Bisnis tidak ditemukan")
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki izin untuk tindakan ini")
    return role


def _link(label: str, param: str, token: str) -> None:
    if get_settings().reset_link_log:
        log.warning("Tautan %s: %s", label, get_settings().frontend_url.rstrip("/") + "/login?" + urlencode({param: token}))


def set_session(response: Response, user: dict) -> None:
    s = get_settings()
    response.set_cookie(COOKIE, get_accounts().session(user), max_age=s.session_days * 86400,
                        httponly=True, secure=s.frontend_url.startswith("https://"), samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


@router.get("/auth/session")
def session(request: Request, response: Response) -> dict:
    s = get_settings()
    if not s.auth_enabled:
        return {"enabled": False, "user": None, "registration_enabled": False}
    token = request.cookies.get(COOKIE, "")
    user = get_accounts().user_for_session(token)
    if user:
        response.set_cookie(COOKIE, token, max_age=max(0, int(user["session_expires"] - time.time())),
                            httponly=True, secure=s.frontend_url.startswith("https://"), samesite="lax", path="/")
    return {"enabled": True, "user": public_user(user) if user else None,
            "registration_enabled": s.registration_enabled}


@router.post("/auth/register")
def register(body: Register, request: Request, response: Response) -> dict:
    if not get_settings().auth_enabled or not get_settings().registration_enabled:
        raise HTTPException(status_code=403, detail="Pendaftaran belum dibuka")
    email = _email(body.email)
    _rate_limit(request, email)
    _password(body.password)
    name, business = body.name.strip(), body.business.strip()
    if not name or not business:
        raise HTTPException(status_code=422, detail="Nama dan nama bisnis wajib diisi")
    try:
        user = get_accounts().register(email, body.password, name, business)
    except ValueError:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar. Silakan masuk.") from None
    set_session(response, user)
    return public_user(user)


@router.post("/auth/login")
def login(body: Login, request: Request, response: Response) -> dict:
    if not get_settings().auth_enabled:
        raise HTTPException(status_code=409, detail="Login belum diaktifkan")
    email = _email(body.email)
    _rate_limit(request, email)
    user = get_accounts().get("user-" + digest(email))
    # Always perform the expensive password hash, even for an unknown email.
    stored = user["password"] if user else hash_password("dummy-password-for-timing", "0" * 32)
    if not password_matches(body.password, stored) or not user:
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    old = request.cookies.get(COOKIE)
    if old:
        get_accounts().delete("session-" + digest(old))
    set_session(response, user)
    return public_user(user)


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(COOKIE, "")
    if token:
        get_accounts().delete("session-" + digest(token))
    _clear_cookie(response)
    return {"ok": True}


@router.patch("/auth/profile")
def update_profile(body: Profile, request: Request, user=Depends(current_user)) -> dict:
    if not body.name.strip() or not body.business.strip():
        raise HTTPException(status_code=422, detail="Nama dan nama bisnis wajib diisi")
    if body.business.strip() != user["business"]:
        _role(user, user["workspace_id"], MANAGERS)
    get_accounts().update_profile(user["email"], user["workspace_id"], body.name.strip(), body.business.strip())
    return public_user(get_accounts().user_for_session(request.cookies[COOKIE]))


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class ResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class PasswordReset(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class EmailToken(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class AccountDeletion(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/password")
def change_password(body: PasswordChange, request: Request, user=Depends(current_user)) -> dict:
    _password(body.new_password)
    _rate_limit(request, user["email"])
    try:
        get_accounts().change_password(user["email"], body.current_password, body.new_password, request.cookies[COOKIE])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"ok": True}


@router.post("/auth/sessions/revoke")
def revoke_sessions(request: Request, user=Depends(current_user)) -> dict:
    get_accounts().revoke_sessions(user["email"], keep=request.cookies[COOKIE])
    return {"ok": True}


@router.post("/auth/password/reset-request", status_code=202)
def reset_request(body: ResetRequest, request: Request) -> dict:
    email = _email(body.email)
    _rate_limit(request, email)
    if get_settings().auth_enabled:
        token = get_accounts().reset_token(email)
        if token:
            _link("atur ulang kata sandi", "reset", token)
    return {"ok": True}


@router.post("/auth/password/reset")
def reset_password(body: PasswordReset, request: Request, response: Response) -> dict:
    _password(body.new_password)
    try:
        get_accounts().reset_password(body.token, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    _clear_cookie(response)
    return {"ok": True}


@router.post("/auth/verify-email/request")
def verify_email_request(user=Depends(current_user)) -> dict:
    if user.get("email_verified", True):
        return {"ok": True, "email_verified": True}
    _link("verifikasi email", "verify", get_accounts().verify_token(user["email"]))
    return {"ok": True, "email_verified": False}


@router.post("/auth/verify-email")
def verify_email(body: EmailToken) -> dict:
    try:
        get_accounts().verify_email(body.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"ok": True}


def _release_channels(workspace: str) -> None:
    for provider in PROVIDERS:
        try:
            get_oauth().disconnect(workspace, provider)
        except ValueError:
            get_accounts().delete(f"connection-{workspace}-{provider}")


@router.delete("/auth/account")
def delete_account(body: AccountDeletion, request: Request, response: Response, user=Depends(current_user)) -> dict:
    _rate_limit(request, user["email"])
    if not get_accounts().check_password(user["email"], body.password):
        raise HTTPException(status_code=400, detail="Kata sandi salah")
    for workspace in get_accounts().delete_account(user["email"]):
        _release_channels(workspace)
    get_accounts().delete("session-" + digest(request.cookies[COOKIE]))
    _clear_cookie(response)
    return {"ok": True}


class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(default="", max_length=60)
    description: str = Field(default="", max_length=2000)
    service_area: str = Field(default="", max_length=200)
    hours: str = Field(default="", max_length=120)


def _profile(profile: BusinessProfile | None, *, partial: bool = False) -> dict | None:
    if profile is None:
        return None
    return {key: value.strip() for key, value in profile.model_dump(exclude_unset=partial).items()}


class WorkspaceName(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    profile: BusinessProfile | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    profile: BusinessProfile | None = None


class WorkspaceSelection(BaseModel):
    workspace_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class MemberInvite(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: str = Field(pattern=r"^(admin|staff)$")


class MemberRole(BaseModel):
    role: str = Field(pattern=r"^(admin|staff)$")


@router.get("/workspaces")
def workspaces(user=Depends(current_user)) -> dict:
    return {"active": user["workspace_id"], "workspaces": get_accounts().spaces(user)}


@router.post("/workspaces")
def add_workspace(body: WorkspaceName, request: Request, user=Depends(current_user)) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nama bisnis wajib diisi")
    try:
        workspace = get_accounts().add_workspace(user["email"], name, _profile(body.profile))
        get_accounts().select_workspace(request.cookies[COOKIE], workspace["id"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return workspace


@router.post("/workspaces/select")
def select_workspace(body: WorkspaceSelection, request: Request, user=Depends(current_user)) -> dict:
    try:
        get_accounts().select_workspace(request.cookies[COOKIE], body.workspace_id)
    except ValueError:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke bisnis ini") from None
    return {"ok": True}


def _workspace_payload(workspace: str, role: str) -> dict:
    record = get_accounts().workspace(workspace)
    return {"id": workspace, "name": record["name"], "role": role, "profile": dict(record.get("profile") or {})}


@router.get("/workspaces/{workspace_id}")
def workspace_detail(workspace_id: str, user=Depends(current_user)) -> dict:
    return _workspace_payload(workspace_id, _role(user, workspace_id))


@router.patch("/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, body: WorkspaceUpdate, user=Depends(current_user)) -> dict:
    role = _role(user, workspace_id, MANAGERS)
    name = body.name.strip() if body.name is not None else None
    if name == "":
        raise HTTPException(status_code=422, detail="Nama bisnis wajib diisi")
    try:
        get_accounts().update_workspace(workspace_id, name=name, profile=_profile(body.profile, partial=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return _workspace_payload(workspace_id, role)


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, request: Request, user=Depends(current_user)) -> dict:
    _role(user, workspace_id, ("owner",))
    if len(user["workspaces"]) <= 1:
        raise HTTPException(status_code=409, detail="Bisnis terakhir tidak bisa dihapus. Buat bisnis lain terlebih dahulu.")
    _release_channels(workspace_id)
    store_for_workspace(workspace_id).audit("workspace_archived", get_accounts().workspace(workspace_id)["name"], actor=user["email"])
    get_accounts().archive_workspace(workspace_id)
    current = get_accounts().user_for_session(request.cookies[COOKIE])
    return {"ok": True, "active": current["workspace_id"] if current else None}


@router.get("/workspaces/{workspace_id}/members")
def list_members(workspace_id: str, user=Depends(current_user)) -> dict:
    _role(user, workspace_id)
    return {"members": get_accounts().members(workspace_id)}


def _member_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404 if isinstance(exc, LookupError) else 409, detail=str(exc))


@router.post("/workspaces/{workspace_id}/members")
def invite_member(workspace_id: str, body: MemberInvite, user=Depends(current_user)) -> dict:
    _role(user, workspace_id, MANAGERS)
    try:
        return get_accounts().invite(workspace_id, _email(body.email), body.role)
    except (LookupError, ValueError) as exc:
        raise _member_error(exc) from None


@router.patch("/workspaces/{workspace_id}/members/{email}")
def update_member(workspace_id: str, email: str, body: MemberRole, user=Depends(current_user)) -> dict:
    _role(user, workspace_id, ("owner",))
    try:
        return get_accounts().set_role(workspace_id, _email(email), body.role)
    except (LookupError, ValueError) as exc:
        raise _member_error(exc) from None


@router.delete("/workspaces/{workspace_id}/members/{email}")
def remove_member(workspace_id: str, email: str, user=Depends(current_user)) -> dict:
    email = _email(email)
    _role(user, workspace_id, ROLES if email == user["email"] else MANAGERS)
    try:
        get_accounts().remove_member(workspace_id, email)
    except (LookupError, ValueError) as exc:
        raise _member_error(exc) from None
    return {"ok": True}


def _provider(provider: str) -> str:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Kanal tidak mendukung login API")
    return provider


def _in_test_mode(workspace: str) -> bool:
    return test_mode_active(get_settings(), store_for_workspace(workspace))


def _no_test_mode(workspace: str) -> None:
    if _in_test_mode(workspace):
        raise HTTPException(status_code=409, detail="Mode pengujian aktif. Matikan mode pengujian untuk menghubungkan akun asli.")


class TestModeRequest(BaseModel):
    enabled: bool


def _test_mode_payload(workspace: str) -> dict:
    settings = get_settings()
    return {"available": settings.test_mode_enabled, "enabled": _in_test_mode(workspace),
            "accounts": [{"provider": a["provider"], "channel": a["channel"], "configured": a["configured"]}
                         for a in env_accounts(settings).values()]}


@router.get("/test-mode")
def get_test_mode(user=Depends(current_user)) -> dict:
    return _test_mode_payload(user["workspace_id"])


@router.put("/test-mode")
def set_test_mode(body: TestModeRequest, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    if body.enabled and not get_settings().test_mode_enabled:
        raise HTTPException(status_code=403, detail="Mode pengujian belum diizinkan di server ini (OMNILEAD_TEST_MODE_ENABLED).")
    store = store_for_workspace(user["workspace_id"])
    settings = store.get_settings()
    settings.test_mode = body.enabled
    store.save_settings(settings)
    store.audit("test_mode_on" if body.enabled else "test_mode_off",
                "Mode pengujian memakai akun dari .env" if body.enabled else "Kembali memakai akun yang dihubungkan",
                actor=user["email"])
    return _test_mode_payload(user["workspace_id"])


@router.get("/connections")
def connections(user=Depends(current_user)) -> list[dict]:
    if _in_test_mode(user["workspace_id"]):
        return env_statuses(get_settings())
    return get_oauth().statuses(user["workspace_id"])


@router.post("/connections/{provider}/start")
def connect(provider: str, request: Request, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    _no_test_mode(user["workspace_id"])
    try:
        return get_oauth().start(_provider(provider), user["workspace_id"], request.cookies[COOKIE])
    except OAuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/auth/oauth/{provider}/callback")
def callback(provider: str, request: Request, code: str = "", state: str = "", error: str = ""):
    provider = _provider(provider)
    result = "connected"
    try:
        user = current_user(request)
        if error or not code:
            get_accounts().consume_state(state, provider, request.cookies.get(COOKIE, ""))
            result = "cancelled"
        else:
            result = get_oauth().complete(provider, code, state, request.cookies[COOKIE], user["workspace_id"])
            if result == "connected":
                store_for_workspace(user["workspace_id"]).audit("channel_connected", provider, actor=user["email"], channel="email" if provider == "gmail" else provider)
    except (ValueError, HTTPException):
        result = "failed"
    # Fixed destination and codes only: no provider error text, tokens, or open redirect.
    url = get_settings().frontend_url.rstrip("/") + "/dashboard/integrasi?" + urlencode({"connection": result, "provider": provider})
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


class WhatsAppCode(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=20, max_length=256)


class WhatsAppSelection(BaseModel):
    selection: str = Field(min_length=20, max_length=256)
    account_id: str = Field(pattern=r"^\d{1,64}$")
    pin: str = Field(default="", max_length=6)


@router.post("/connections/whatsapp/exchange")
def whatsapp_exchange(body: WhatsAppCode, request: Request, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    try:
        return get_oauth().whatsapp_exchange(user["workspace_id"], request.cookies[COOKIE], body.state, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/connections/whatsapp/select")
def whatsapp_select(body: WhatsAppSelection, request: Request, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    try:
        get_oauth().whatsapp_select(user["workspace_id"], request.cookies[COOKIE], body.selection, body.account_id, body.pin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    store_for_workspace(user["workspace_id"]).audit("channel_connected", "whatsapp", actor=user["email"], channel="whatsapp")
    return {"ok": True}


class WhatsAppManual(BaseModel):
    phone_number_id: str = Field(pattern=r"^\d{5,64}$")
    waba_id: str = Field(pattern=r"^\d{5,64}$")
    access_token: str = Field(min_length=20, max_length=1024, pattern=r"^\S+$")


@router.post("/connections/whatsapp/manual")
def whatsapp_manual(body: WhatsAppManual, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    try:
        get_oauth().whatsapp_manual(user["workspace_id"], body.phone_number_id, body.waba_id, body.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    store_for_workspace(user["workspace_id"]).audit("channel_connected", "whatsapp (nomor uji)", actor=user["email"], channel="whatsapp")
    return {"ok": True}


class FacebookSelection(BaseModel):
    page_id: str = Field(pattern=r"^\d{1,64}$")


@router.get("/connections/facebook/pages")
def facebook_pages(request: Request, user=Depends(current_user)) -> dict:
    try:
        return get_oauth().facebook_pages(user["workspace_id"], request.cookies[COOKIE])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/connections/facebook/select")
def facebook_select(body: FacebookSelection, request: Request, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    try:
        get_oauth().facebook_select(user["workspace_id"], request.cookies[COOKIE], body.page_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    store_for_workspace(user["workspace_id"]).audit("channel_connected", "facebook", actor=user["email"], channel="facebook")
    return {"ok": True}


@router.delete("/connections/{provider}")
def disconnect(provider: str, user=Depends(current_user)) -> dict:
    _role(user, user["workspace_id"], MANAGERS)
    _no_test_mode(user["workspace_id"])
    get_oauth().disconnect(user["workspace_id"], _provider(provider))
    store_for_workspace(user["workspace_id"]).audit("channel_disconnected", provider, actor=user["email"], channel="email" if provider == "gmail" else provider)
    return {"ok": True}
