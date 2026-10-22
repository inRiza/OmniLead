"""Komponen bersama (singleton) untuk seluruh aplikasi."""

import hmac
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Request

from omnilead.agent_client import AgentClient, google_id_token_provider
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


def registry_for_workspace(workspace: str) -> Registry:
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


def get_executor(registry=Depends(get_registry), store=Depends(get_store)) -> Executor:
    return Executor(registry, store)


@lru_cache
def get_agent_client() -> AgentClient:
    s = get_settings()
    provider = google_id_token_provider(s.agent_url) if s.agent_auth == "oidc" else None
    return AgentClient(s.agent_url, s.agent_api_key, s.agent_timeout_s, token_provider=provider)


def get_ingest(store=Depends(get_store), queue=Depends(get_queue), agent=Depends(get_agent_client),
               executor=Depends(get_executor)) -> IngestService:
    return IngestService(store, queue, agent, executor)


def ingest_for_workspace(workspace: str) -> IngestService:
    store = store_for_workspace(workspace)
    return IngestService(store, ApprovalQueue(store, account_bindings=account_bindings(workspace)), get_agent_client(),
                         Executor(registry_for_workspace(workspace), store))


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
