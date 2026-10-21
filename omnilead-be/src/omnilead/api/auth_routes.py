import re
import time
from collections import defaultdict, deque
from threading import Lock
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from omnilead.accounts import COOKIE, digest, hash_password, password_matches
from omnilead.api.deps import current_user, get_accounts, get_oauth, store_for_workspace
from omnilead.config import get_settings
from omnilead.oauth import OAuthError, PROVIDERS

router = APIRouter(tags=["accounts"])
_attempts: dict[str, deque] = defaultdict(deque)
_attempt_lock = Lock()


def check_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    settings = get_settings()
    allowed = {settings.frontend_url.rstrip("/"), *settings.cors_origins}
    if (origin and origin.rstrip("/") not in allowed) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Permintaan berasal dari situs lain")


def _rate_limit(request: Request, email: str) -> None:
    now = time.time()
    keys = ["ip:" + (request.client.host if request.client else "local"), "email:" + digest(email.lower())]
    with _attempt_lock:
        # Bound memory even when random emails are submitted.
        for key in list(_attempts):
            while _attempts[key] and _attempts[key][0] <= now - 60:
                _attempts[key].popleft()
            if not _attempts[key]:
                del _attempts[key]
        for key in keys:
            if len(_attempts[key]) >= (30 if key.startswith("ip:") else 8):
                raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Tunggu satu menit.")
        for key in keys:
            _attempts[key].append(now)


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
    return {**{key: user[key] for key in ("id", "workspace_id", "email", "name", "business")},
            "workspaces": get_accounts().spaces(user)}


def set_session(response: Response, user: dict) -> None:
    s = get_settings()
    response.set_cookie(COOKIE, get_accounts().session(user), max_age=s.session_days * 86400,
                        httponly=True, secure=s.frontend_url.startswith("https://"), samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


@router.get("/auth/session")
def session(request: Request) -> dict:
    s = get_settings()
    if not s.auth_enabled:
        return {"enabled": False, "user": None, "registration_enabled": False}
    user = get_accounts().user_for_session(request.cookies.get(COOKIE, ""))
    return {"enabled": True, "user": public_user(user) if user else None,
            "registration_enabled": s.registration_enabled}


@router.post("/auth/register")
def register(body: Register, request: Request, response: Response) -> dict:
    if not get_settings().auth_enabled or not get_settings().registration_enabled:
        raise HTTPException(status_code=403, detail="Pendaftaran belum dibuka")
    email = _email(body.email)
    _rate_limit(request, email)
    if len(body.password) < 12:
        raise HTTPException(status_code=422, detail="Gunakan kata sandi minimal 12 karakter")
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
    response.delete_cookie(COOKIE, path="/", secure=get_settings().frontend_url.startswith("https://"), httponly=True, samesite="lax")
    return {"ok": True}


@router.patch("/auth/profile")
def update_profile(body: Profile, request: Request, user=Depends(current_user)) -> dict:
    if not body.name.strip() or not body.business.strip():
        raise HTTPException(status_code=422, detail="Nama dan nama bisnis wajib diisi")
    get_accounts().update_profile(user["email"], user["workspace_id"], body.name.strip(), body.business.strip())
    return public_user(get_accounts().user_for_session(request.cookies[COOKIE]))


class WorkspaceName(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceSelection(BaseModel):
    workspace_id: str = Field(pattern=r"^[a-f0-9]{32}$")


@router.get("/workspaces")
def workspaces(user=Depends(current_user)) -> dict:
    return {"active": user["workspace_id"], "workspaces": get_accounts().spaces(user)}


@router.post("/workspaces")
def add_workspace(body: WorkspaceName, request: Request, user=Depends(current_user)) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nama bisnis wajib diisi")
    try:
        workspace = get_accounts().add_workspace(user["email"], name)
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


def _provider(provider: str) -> str:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Kanal tidak mendukung login API")
    return provider


@router.get("/connections")
def connections(user=Depends(current_user)) -> list[dict]:
    return get_oauth().statuses(user["workspace_id"])


@router.post("/connections/{provider}/start")
def connect(provider: str, request: Request, user=Depends(current_user)) -> dict:
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
    try:
        return get_oauth().whatsapp_exchange(user["workspace_id"], request.cookies[COOKIE], body.state, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/connections/whatsapp/select")
def whatsapp_select(body: WhatsAppSelection, request: Request, user=Depends(current_user)) -> dict:
    try:
        get_oauth().whatsapp_select(user["workspace_id"], request.cookies[COOKIE], body.selection, body.account_id, body.pin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    store_for_workspace(user["workspace_id"]).audit("channel_connected", "whatsapp", actor=user["email"], channel="whatsapp")
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
    try:
        get_oauth().facebook_select(user["workspace_id"], request.cookies[COOKIE], body.page_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    store_for_workspace(user["workspace_id"]).audit("channel_connected", "facebook", actor=user["email"], channel="facebook")
    return {"ok": True}


@router.delete("/connections/{provider}")
def disconnect(provider: str, user=Depends(current_user)) -> dict:
    get_oauth().disconnect(user["workspace_id"], _provider(provider))
    store_for_workspace(user["workspace_id"]).audit("channel_disconnected", provider, actor=user["email"], channel="email" if provider == "gmail" else provider)
    return {"ok": True}
