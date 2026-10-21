"""Endpoint untuk Cloud Scheduler. Bukan untuk FE.

Autentikasi: `Authorization: Bearer <OMNILEAD_SCHEDULER_TOKEN>`, atau token OIDC
Google bila `OMNILEAD_SCHEDULER_OIDC_AUDIENCE` diisi (Scheduler mengirim OIDC
dari service account). Keduanya kosong -> endpoint ditutup (403).
"""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException

from omnilead.api.deps import get_ingest, get_queue, get_registry, get_store
from omnilead.api.webhooks import poll_gmail
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


@router.post("/followups")
def followups(store: Store = Depends(get_store), queue: ApprovalQueue = Depends(get_queue)) -> dict:
    return run_followups(store, queue)


@router.post("/gmail-poll")
def gmail_poll(
    registry: Registry = Depends(get_registry), ingest: IngestService = Depends(get_ingest)
) -> dict:
    return {"events": poll_gmail(registry, ingest)}


@router.post("/gmail-watch")
def gmail_watch(registry: Registry = Depends(get_registry)) -> dict:
    gmail = registry.gmail()
    if gmail is None or not gmail.configured:
        return {"skipped": "Gmail belum terhubung"}
    try:
        return gmail.watch()
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
