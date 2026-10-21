"""Endpoint HTTP OmniLead.

Kanal & handoff
  GET  /channels, /channels/{ch}/posts, /channels/{ch}/comments
  POST /handoff/paste                -> tempel pesan kanal tanpa API
Event & lead
  POST /events                       -> event masuk (dedup, identitas, panggil agen)
  GET  /events, POST /events/{id}/analyze
  GET  /leads, /leads/{id}           -> profil + timeline
Antrean persetujuan
  POST /actions/propose, GET /actions?status=
  POST /actions/{id}/approve | reject | retry | sent ; GET /actions/{id}/handoff
Kendali
  GET/POST /settings/pause ; GET/PATCH /settings ; PATCH /settings/channels/{ch}
  GET  /audit
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from omnilead.api.deps import (
    get_agent_client,
    get_executor,
    get_ingest,
    get_queue,
    get_registry,
    get_store,
)
from omnilead.agent_client import AgentClient, AgentUnavailable
from omnilead.api.schemas import (
    AppSettingsPatch,
    PasteEventRequest,
    PasteImageRequest,
    ApproveRequest,
    ChannelSettingsRequest,
    PasteRequest,
    PauseRequest,
    RejectRequest,
)
from omnilead.approvals.executor import ChannelDisabled, Executor, Paused, RateLimited
from omnilead.approvals.merge import can_undo, undo_merge
from omnilead.approvals.queue import ApprovalQueue, InvalidTransition
from omnilead.connectors import handoff
from omnilead.connectors.base import ActionNotSupported, ConnectorError, NotConnected
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.scheduler import daily_summary
from omnilead.models import (
    Action,
    ActionStatus,
    AppSettings,
    AuditEntry,
    Channel,
    ChannelStatus,
    Comment,
    Event,
    EventIn,
    Lead,
    Post,
    ProposedAction,
    Sender,
)
from omnilead.store import Store

router = APIRouter()

_MIN_TS = datetime.min.replace(tzinfo=timezone.utc)

NOT_FOUND = HTTPException(status_code=404, detail="Tidak ditemukan")


def _run_executor(executor: Executor, action: Action) -> Action:
    try:
        return executor.execute(action)
    except Paused as exc:
        raise HTTPException(status_code=423, detail=str(exc))
    except ChannelDisabled as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc))


# --- kanal ---


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


# --- event & lead ---


@router.post("/events", response_model=Event)
def post_event(
    ev: EventIn, ingest: IngestService = Depends(get_ingest)
) -> Event:
    event, _duplicate = ingest.ingest(ev)
    return event


@router.post("/events/paste", response_model=Event)
def paste_event(
    req: PasteEventRequest, ingest: IngestService = Depends(get_ingest)
) -> Event:
    """Kanal tanpa API: pengguna menempel teks pesan; diproses seperti event biasa."""
    ev = EventIn(
        channel=req.channel,
        kind="message",
        external_id=f"paste-{uuid.uuid4().hex}",
        sender=Sender(handle=req.handle, name=req.name),
        text=req.text.strip(),
        post_ref=req.post_ref,
        meta={"source": "paste"},
    )
    event, _ = ingest.ingest(ev)
    return event


@router.post("/events/paste-image", response_model=Event)
def paste_image(
    req: PasteImageRequest,
    ingest: IngestService = Depends(get_ingest),
    agent: AgentClient = Depends(get_agent_client),
) -> Event:
    """Screenshot DM dari kanal tanpa API: Gemini mengekstrak pengirim dan isi."""
    try:
        data = agent.extract(
            {"image_base64": req.image_base64, "mime_type": req.mime_type, "channel": req.channel.value}
        )
    except AgentUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Ekstraksi screenshot gagal: {exc}")
    text = str(data.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=422, detail="Isi pesan tidak terbaca dari screenshot")
    ev = EventIn(
        channel=req.channel,
        kind="message",
        external_id=f"paste-{uuid.uuid4().hex}",
        sender=Sender(handle=str(data.get("handle") or ""), name=data.get("name")),
        text=text,
        meta={"source": "screenshot"},
    )
    event, _ = ingest.ingest(ev)
    return event


@router.get("/content-ideas")
def content_ideas(
    days: int = Query(14, ge=1, le=60),
    store: Store = Depends(get_store),
    agent: AgentClient = Depends(get_agent_client),
) -> dict:
    """Ide konten (draf saja) dari pertanyaan pelanggan beberapa hari terakhir."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    messages = [
        {"text": e.text, "channel": e.channel.value}
        for e in store.list_events(limit=300)
        if e.ts is None or (e.ts if e.ts.tzinfo else e.ts.replace(tzinfo=timezone.utc)) >= cutoff
    ]
    try:
        return agent.content_ideas({"messages": messages})
    except AgentUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Service agen tidak tersedia: {exc}")


@router.get("/summary/today")
def summary_today(store: Store = Depends(get_store)) -> list[dict]:
    """Hal yang perlu ditangani hari ini, urut prioritas."""
    return daily_summary(store)


@router.get("/events", response_model=list[Event])
def list_events(
    lead_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    store: Store = Depends(get_store),
) -> list[Event]:
    return store.list_events(lead_id=lead_id, limit=limit)


@router.post("/events/{event_id}/analyze", response_model=Event)
def reanalyze(
    event_id: str,
    store: Store = Depends(get_store),
    ingest: IngestService = Depends(get_ingest),
) -> Event:
    event = store.get_event(event_id)
    if event is None:
        raise NOT_FOUND
    return ingest.process(event)


@router.get("/leads", response_model=list[Lead])
def list_leads(store: Store = Depends(get_store)) -> list[Lead]:
    return store.list_leads()


@router.get("/leads/{lead_id}")
def get_lead(lead_id: str, store: Store = Depends(get_store)) -> dict:
    lead = store.get_lead(lead_id)
    if lead is None:
        raise NOT_FOUND
    events = store.list_events(lead_id=lead_id, limit=200)
    actions = [a for a in store.list_actions() if a.lead_id == lead_id]
    timeline = [
        {"ts": e.ts, "direction": "in", "channel": e.channel, "text": e.text, "event_id": e.id}
        for e in events
    ] + [
        {"ts": a.created_at, "direction": "out", "channel": a.channel, "text": a.text,
         "action_id": a.id, "status": a.status}
        for a in actions
        if a.result_ref and a.text
    ]
    timeline.sort(key=lambda t: t["ts"] or _MIN_TS, reverse=True)
    audit = [x for x in store.list_audit(limit=500) if x.lead_id == lead_id]
    evidence = [x for x in audit if x.event == "identity_merged"]
    merges = [
        {
            "action_id": a.id,
            "source_name": a.payload["undo"]["source"].get("name"),
            "evidence": a.payload.get("evidence", []),
        }
        for a in store.list_actions()
        if can_undo(a) and a.payload.get("target_lead_id") == lead_id
    ]
    return {
        "lead": lead,
        "timeline": timeline,
        "actions": actions,
        "merge_evidence": evidence,
        "undoable_merges": merges,
    }


# --- antrean persetujuan ---


@router.post("/actions/propose", response_model=Action)
def propose(
    req: ProposedAction, queue: ApprovalQueue = Depends(get_queue)
) -> Action:
    return queue.propose(req)


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
    store: Store = Depends(get_store),
) -> Action:
    if store.get_settings().paused:
        raise HTTPException(status_code=423, detail="Agent dijeda. Semua aksi ditahan.")
    try:
        action = queue.approve(action_id, edited_text=req.edited_text)
    except KeyError:
        raise NOT_FOUND
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _run_executor(executor, action)


@router.post("/actions/{action_id}/reject", response_model=Action)
def reject(
    action_id: str,
    req: RejectRequest,
    queue: ApprovalQueue = Depends(get_queue),
) -> Action:
    try:
        return queue.reject(action_id, req.reason)
    except KeyError:
        raise NOT_FOUND
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/actions/{action_id}/retry", response_model=Action)
def retry(
    action_id: str,
    queue: ApprovalQueue = Depends(get_queue),
    executor: Executor = Depends(get_executor),
) -> Action:
    try:
        action = queue.retry(action_id)
    except KeyError:
        raise NOT_FOUND
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _run_executor(executor, action)


@router.post("/actions/{action_id}/sent", response_model=Action)
def mark_sent(
    action_id: str, queue: ApprovalQueue = Depends(get_queue)
) -> Action:
    try:
        return queue.mark_sent_manually(action_id)
    except KeyError:
        raise NOT_FOUND
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/actions/{action_id}/undo-merge", response_model=Action)
def undo_merge_route(action_id: str, store: Store = Depends(get_store)) -> Action:
    """Pisah profil: batalkan merge identitas yang sudah dieksekusi."""
    try:
        return undo_merge(store, action_id)
    except KeyError:
        raise NOT_FOUND
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/actions/{action_id}/handoff")
def action_handoff(
    action_id: str, store: Store = Depends(get_store)
) -> dict:
    action = store.get_action(action_id)
    if action is None:
        raise NOT_FOUND
    return handoff.build_handoff(action.channel, action.text)


# --- kendali ---


@router.get("/settings", response_model=AppSettings)
def get_settings_(store: Store = Depends(get_store)) -> AppSettings:
    return store.get_settings()


@router.patch("/settings", response_model=AppSettings)
def patch_settings(
    patch: AppSettingsPatch, store: Store = Depends(get_store)
) -> AppSettings:
    s = store.get_settings()
    for field, value in patch.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    store.save_settings(s)
    store.audit("settings_changed", str(patch.model_dump(exclude_none=True)), actor="owner")
    return s


@router.get("/settings/pause")
def get_pause(store: Store = Depends(get_store)) -> dict:
    return {"paused": store.get_settings().paused}


@router.post("/settings/pause")
def set_pause(
    req: PauseRequest,
    store: Store = Depends(get_store),
    ingest: IngestService = Depends(get_ingest),
) -> dict:
    s = store.get_settings()
    s.paused = req.paused
    store.save_settings(s)
    store.audit("paused" if req.paused else "resumed", "Pause Agent", actor="owner")
    reprocessed = 0
    if not req.paused:
        reprocessed = len(ingest.reprocess_held())
    return {"paused": s.paused, "reprocessed_events": reprocessed}


@router.patch("/settings/channels/{channel}", response_model=AppSettings)
def patch_channel(
    channel: Channel,
    req: ChannelSettingsRequest,
    store: Store = Depends(get_store),
) -> AppSettings:
    s = store.get_settings()
    if req.enabled is False and channel not in s.disabled_channels:
        s.disabled_channels.append(channel)
    elif req.enabled is True and channel in s.disabled_channels:
        s.disabled_channels.remove(channel)
    store.save_settings(s)
    store.audit(
        "channel_switch",
        f"{channel.value} {'aktif' if req.enabled else 'dimatikan'}",
        actor="owner",
        channel=channel.value,
    )
    return s


@router.get("/agent/health")
def agent_health(agent: AgentClient = Depends(get_agent_client)) -> dict:
    try:
        return {"reachable": True, **agent.health()}
    except AgentUnavailable as exc:
        return {"reachable": False, "error": str(exc)}


@router.get("/audit", response_model=list[AuditEntry])
def audit(
    limit: int = Query(100, ge=1, le=500),
    channel: str | None = None,
    store: Store = Depends(get_store),
) -> list[AuditEntry]:
    return store.list_audit(limit, channel=channel)

