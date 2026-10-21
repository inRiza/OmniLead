"""Endpoint HTTP OmniLead.

Alur utama:
  GET  /channels                     -> status & kapabilitas tiap kanal
  GET  /channels/{ch}/posts          -> daftar post (jika didukung)
  GET  /channels/{ch}/comments       -> baca komentar (jika didukung)
  POST /handoff/paste                -> tempel pesan kanal tanpa API -> jadi komentar
  POST /actions/propose              -> agen/pengguna mengusulkan aksi keluar
  GET  /actions?status=pending       -> antrean persetujuan
  POST /actions/{id}/approve         -> Setujui (opsional edit) lalu eksekusi
  POST /actions/{id}/reject          -> Tolak dengan alasan
  POST /actions/{id}/sent            -> tandai aksi handoff sudah dikirim manual
  GET  /audit                        -> audit log
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from omnilead.api.deps import get_executor, get_queue, get_registry, get_store
from omnilead.api.schemas import (
    ApproveRequest,
    PasteRequest,
    ProposeRequest,
    RejectRequest,
)
from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.connectors import handoff
from omnilead.connectors.base import ActionNotSupported, ConnectorError, NotConnected
from omnilead.connectors.registry import Registry
from omnilead.models import (
    Action,
    ActionStatus,
    AuditEntry,
    Channel,
    ChannelStatus,
    Comment,
    Post,
    ProposedAction,
)
from omnilead.store import Store

router = APIRouter()


@router.get("/channels", response_model=list[ChannelStatus])
def channels(reg: Registry = Depends(get_registry)) -> list[ChannelStatus]:
    return [c.status() for c in reg.all()]


@router.get("/channels/{channel}/posts", response_model=list[Post])
def list_posts(
    channel: Channel,
    limit: int = Query(10, ge=1, le=50),
    reg: Registry = Depends(get_registry),
) -> list[Post]:
    try:
        return reg.get(channel).list_posts(limit=limit)
    except ActionNotSupported as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except NotConnected as exc:
        raise HTTPException(status_code=424, detail=str(exc))
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/channels/{channel}/comments", response_model=list[Comment])
def read_comments(
    channel: Channel,
    post_ref: str = Query(..., description="URL/ID post"),
    limit: int = Query(50, ge=1, le=200),
    reg: Registry = Depends(get_registry),
) -> list[Comment]:
    try:
        return reg.get(channel).read_comments(post_ref, limit=limit)
    except ActionNotSupported as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except NotConnected as exc:
        raise HTTPException(status_code=424, detail=str(exc))
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/handoff/paste", response_model=Comment)
def paste(req: PasteRequest) -> Comment:
    return handoff.ingest_pasted_text(
        channel=req.channel,
        post_ref=req.post_ref,
        author_handle=req.author_handle,
        text=req.text,
    )


@router.post("/actions/propose", response_model=Action)
def propose(
    req: ProposeRequest, queue: ApprovalQueue = Depends(get_queue)
) -> Action:
    proposal = ProposedAction(**req.model_dump())
    return queue.propose(proposal)


@router.get("/actions", response_model=list[Action])
def list_actions(
    status: ActionStatus | None = None,
    store: Store = Depends(get_store),
) -> list[Action]:
    return store.list_actions(status)


@router.post("/actions/{action_id}/approve", response_model=Action)
def approve(
    action_id: str,
    req: ApproveRequest,
    queue: ApprovalQueue = Depends(get_queue),
    executor: Executor = Depends(get_executor),
) -> Action:
    try:
        action = queue.approve(action_id, edited_text=req.edited_text)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aksi tidak ditemukan")
    return executor.execute(action)


@router.post("/actions/{action_id}/reject", response_model=Action)
def reject(
    action_id: str,
    req: RejectRequest,
    queue: ApprovalQueue = Depends(get_queue),
) -> Action:
    try:
        return queue.reject(action_id, req.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aksi tidak ditemukan")


@router.post("/actions/{action_id}/sent", response_model=Action)
def mark_sent(
    action_id: str, queue: ApprovalQueue = Depends(get_queue)
) -> Action:
    try:
        return queue.mark_sent_manually(action_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Aksi tidak ditemukan")


@router.get("/actions/{action_id}/handoff")
def action_handoff(
    action_id: str, store: Store = Depends(get_store)
) -> dict:
    action = store.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Aksi tidak ditemukan")
    return handoff.build_handoff(action.channel, action.text)


@router.get("/audit", response_model=list[AuditEntry])
def audit(
    limit: int = Query(100, ge=1, le=500),
    store: Store = Depends(get_store),
) -> list[AuditEntry]:
    return store.list_audit(limit)
