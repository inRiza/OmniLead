"""Komponen bersama (singleton) untuk seluruh aplikasi."""

import hmac
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Request

from omnilead.agent_client import AgentClient, google_id_token_provider
from omnilead.approvals.auto import AutoSender
from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.config import get_settings
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.store import Store
from omnilead.accounts import AccountStore, COOKIE
from omnilead.oauth import OAuthService


@lru_cache
def get_accounts() -> AccountStore:
    return AccountStore(get_settings())


@lru_cache
def get_oauth() -> OAuthService:
    return OAuthService(get_settings(), get_accounts())


def current_user(request: Request) -> dict:
    user = get_accounts().user_for_session(request.cookies.get(COOKIE, ""))
    if not user:
        raise HTTPException(status_code=401, detail="Silakan masuk ke OmniLead")
    expected = request.headers.get("x-omnilead-workspace")
    if expected and expected != user["workspace_id"]:
        raise HTTPException(status_code=409, detail="Bisnis aktif berubah. Muat ulang halaman.")
    return user


def workspace_for_request(request: Request | None) -> str:
    if not get_settings().auth_enabled or request is None:
        return "legacy"
    # These endpoints explicitly dispatch verified events/jobs to each workspace.
    if request.url.path.startswith(("/webhooks/", "/scheduler/")):
        return "legacy"
    return current_user(request)["workspace_id"]


@lru_cache(maxsize=128)
def store_for_workspace(workspace: str):
    s = get_settings()
    if s.store == "firestore":
        from omnilead.store_firestore import FirestoreStore

        if workspace == "legacy":
            return FirestoreStore(project=s.firestore_project or None)
        from google.cloud import firestore
        client = firestore.Client(project=s.firestore_project or None)
        return FirestoreStore(client=client.collection("workspaces").document(workspace))
    path = s.db_path if workspace == "legacy" else s.db_path.parent / "workspaces" / f"{workspace}.db"
    return Store(path)


def get_store(request: Request = None):
    workspace = workspace_for_request(request)
    store = store_for_workspace(workspace)
    if workspace != "legacy" and request is not None:
        name = current_user(request)["business"]
        settings = store.get_settings()
        if settings.business_name != name:
            settings.business_name = name
            store.save_settings(settings)
    return store


@lru_cache
def get_platform_http():
    import httpx
    return httpx.Client(timeout=25, follow_redirects=False)


def _test_mode(workspace: str) -> bool:
    from omnilead.test_mode import test_mode_active
    return workspace != "legacy" and test_mode_active(get_settings(), store_for_workspace(workspace))


def registry_for_workspace(workspace: str) -> Registry:
    if _test_mode(workspace):
        from omnilead.test_mode import env_bindings
        registry = Registry(get_settings(), client=get_platform_http())
        registry.account_ids = env_bindings(get_settings())
        return registry
    settings = get_settings() if workspace == "legacy" else get_oauth().connector_settings(workspace)
    def invalid(channel):
        provider = "gmail" if channel.value == "email" else channel.value
        get_oauth().mark_reconnect(workspace, provider)
    registry = Registry(settings, client=get_platform_http(), on_auth_error=invalid if workspace != "legacy" else None)
    if workspace != "legacy":
        registry.account_ids = account_bindings(workspace)
    return registry


def account_bindings(workspace: str) -> dict:
    from omnilead.oauth import CHANNELS
    if _test_mode(workspace):
        from omnilead.test_mode import env_bindings
        return env_bindings(get_settings())
    bindings = {}
    for provider, channel in CHANNELS.items():
        data = get_accounts().connection(workspace, provider)
        bindings[channel] = data["account_id"] if data else ""
    return bindings


def get_registry(request: Request = None) -> Registry:
    return registry_for_workspace(workspace_for_request(request))


def get_queue(request: Request, store=Depends(get_store)) -> ApprovalQueue:
    workspace = workspace_for_request(request)
    if workspace == "legacy":
        return ApprovalQueue(store)
    return ApprovalQueue(store, actor=current_user(request)["email"], account_bindings=account_bindings(workspace))


def browser_sender(workspace: str):
    settings = get_settings()
    if workspace == "legacy" or not settings.browser_enabled or not _test_mode(workspace):
        return None
    from omnilead.instagram_send import send_action
    return lambda action, source: send_action(settings, workspace, action, source)


def get_executor(request: Request, registry=Depends(get_registry), store=Depends(get_store)) -> Executor:
    return Executor(registry, store, browser_sender(workspace_for_request(request)))


@lru_cache
def get_agent_client() -> AgentClient:
    s = get_settings()
    provider = google_id_token_provider(s.agent_url) if s.agent_auth == "oidc" else None
    return AgentClient(s.agent_url, s.agent_api_key, s.agent_timeout_s, token_provider=provider)


def get_auto_sender(store=Depends(get_store), queue=Depends(get_queue), executor=Depends(get_executor)) -> AutoSender:
    return AutoSender(store, queue, executor)


def get_ingest(request: Request, store=Depends(get_store), queue=Depends(get_queue), agent=Depends(get_agent_client),
               executor=Depends(get_executor), auto=Depends(get_auto_sender)) -> IngestService:
    workspace = workspace_for_request(request)
    profile = (lambda: get_accounts().workspace_profile(workspace)) if workspace != "legacy" else None
    return IngestService(store, queue, agent, executor, on_proposed=auto.handle, profile=profile)


def auto_sender_for_workspace(workspace: str) -> AutoSender:
    store = store_for_workspace(workspace)
    queue = ApprovalQueue(store, account_bindings=account_bindings(workspace))
    return AutoSender(store, queue, Executor(registry_for_workspace(workspace), store, browser_sender(workspace)))


def ingest_for_workspace(workspace: str) -> IngestService:
    store = store_for_workspace(workspace)
    queue = ApprovalQueue(store, account_bindings=account_bindings(workspace))
    executor = Executor(registry_for_workspace(workspace), store, browser_sender(workspace))
    auto = AutoSender(store, queue, executor)
    profile = (lambda: get_accounts().workspace_profile(workspace)) if workspace != "legacy" else None
    return IngestService(store, queue, get_agent_client(), executor, on_proposed=auto.handle, profile=profile)


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    """Autentikasi REST untuk FE. Mati jika OMNILEAD_API_KEY kosong (dev)."""
    if get_settings().auth_enabled:
        current_user(request)
        return
    expected = get_settings().api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="API key salah")
