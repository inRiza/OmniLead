"""Endpoint untuk Cloud Scheduler. Bukan untuk FE.

Autentikasi: `Authorization: Bearer <OMNILEAD_SCHEDULER_TOKEN>`, atau token OIDC
Google bila `OMNILEAD_SCHEDULER_OIDC_AUDIENCE` diisi (Scheduler mengirim OIDC
dari service account). Keduanya kosong -> endpoint ditutup (403).
"""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException

from omnilead.api.deps import (get_auto_sender, get_executor, get_ingest, get_queue, get_registry, get_store,
                               get_accounts, auto_sender_for_workspace, store_for_workspace,
                               registry_for_workspace, ingest_for_workspace)
from omnilead.approvals.auto import AutoSender
from omnilead.approvals.dispatch import dispatch
from omnilead.approvals.executor import Executor
from omnilead.api.webhooks import drain_inbox, poll_gmail
from omnilead.dedup import scan_duplicates
from omnilead.instagram_sync import sync_instagram
from omnilead.approvals.queue import ApprovalQueue
from omnilead.config import Settings, get_settings
from omnilead.connectors.base import ConnectorError
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.scheduler import run_followups
from omnilead.store import Store


def _verify_oidc(token: str, audience: str) -> bool:
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        id_token.verify_oauth2_token(token, g_requests.Request(), audience=audience)
        return True
    except Exception:
        return False


def require_scheduler(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        if settings.scheduler_token and hmac.compare_digest(token, settings.scheduler_token):
            return
        if settings.scheduler_oidc_audience and _verify_oidc(token, settings.scheduler_oidc_audience):
            return
    raise HTTPException(status_code=403, detail="Tidak diizinkan")


router = APIRouter(prefix="/scheduler", tags=["scheduler"], dependencies=[Depends(require_scheduler)])


@router.post("/agent-tasks")
def agent_tasks() -> dict:
    from omnilead.task_worker import tick
    return {"workspaces": tick()}


@router.post("/followups")
def followups(store: Store = Depends(get_store), queue: ApprovalQueue = Depends(get_queue)) -> dict:
    if get_settings().auth_enabled:
        return {"workspaces": {w: run_followups(store_for_workspace(w), ApprovalQueue(store_for_workspace(w)))
                               for w in get_accounts().workspace_ids()}}
    return run_followups(store, queue)


@router.post("/dispatch")
def dispatch_actions(
    store: Store = Depends(get_store),
    executor: Executor = Depends(get_executor),
    auto: AutoSender = Depends(get_auto_sender),
) -> dict:
    if get_settings().auth_enabled:
        results = {}
        for w in get_accounts().workspace_ids():
            sender = auto_sender_for_workspace(w)
            results[w] = dispatch(store_for_workspace(w), sender.executor, sender)
        return {"workspaces": results}
    return dispatch(store, executor, auto)


@router.post("/dedup")
def dedup(
    store: Store = Depends(get_store),
    queue: ApprovalQueue = Depends(get_queue),
    auto: AutoSender = Depends(get_auto_sender),
) -> dict:
    if get_settings().auth_enabled:
        results = {}
        for w in get_accounts().workspace_ids():
            sender = auto_sender_for_workspace(w)
            results[w] = len(scan_duplicates(store_for_workspace(w), sender.queue, on_proposed=sender.handle))
        return {"workspaces": results}
    return {"proposed": len(scan_duplicates(store, queue, on_proposed=auto.handle))}


@router.post("/drain-inbox")
def drain(registry: Registry = Depends(get_registry), ingest: IngestService = Depends(get_ingest)) -> dict:
    if get_settings().auth_enabled:
        return {"workspaces": {w: drain_inbox(ingest_for_workspace(w), registry_for_workspace(w))
                               for w in get_accounts().workspace_ids()}}
    return {"processed": drain_inbox(ingest, registry)}


@router.post("/instagram-sync")
def instagram_sync(
    store: Store = Depends(get_store),
    registry: Registry = Depends(get_registry),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    settings = get_settings()
    if settings.auth_enabled:
        return {"workspaces": {w: sync_instagram(store_for_workspace(w), registry_for_workspace(w),
                                                  ingest_for_workspace(w), settings, w)
                               for w in get_accounts().workspace_ids()}}
    return sync_instagram(store, registry, ingest, settings, "legacy")


@router.post("/gmail-poll")
def gmail_poll(
    registry: Registry = Depends(get_registry), ingest: IngestService = Depends(get_ingest)
) -> dict:
    if get_settings().auth_enabled:
        return {"events": sum(poll_gmail(registry_for_workspace(w), ingest_for_workspace(w))
                              for w in get_accounts().workspace_ids())}
    return {"events": poll_gmail(registry, ingest)}


@router.post("/gmail-watch")
def gmail_watch(registry: Registry = Depends(get_registry)) -> dict:
    if get_settings().auth_enabled:
        results = {}
        for workspace in get_accounts().workspace_ids():
            gmail = registry_for_workspace(workspace).gmail()
            if not gmail or not gmail.configured:
                continue
            try:
                results[workspace] = gmail.watch()
            except ConnectorError:
                results[workspace] = {"error": "Gagal memperpanjang akses notifikasi Gmail"}
        return {"workspaces": results}
    gmail = registry.gmail()
    if gmail is None or not gmail.configured:
        return {"skipped": "Gmail belum terhubung"}
    try:
        return gmail.watch()
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
