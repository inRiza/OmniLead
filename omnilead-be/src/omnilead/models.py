"""Model data yang sama untuk semua kanal.

Agen dan FE hanya melihat bentuk ini, tidak peduli connector di baliknya.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Channel(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


# Jalur akses yang diakui. Hanya resmi atau handoff manual.
#   official_api : panggil API resmi platform.
#   handoff      : tidak ada API; manusia menempel pesan masuk dan mengirim sendiri.
AccessPath = Literal["official_api", "handoff"]

ActionName = Literal[
    "list_posts", "read_comments", "post_comment", "reply_comment", "send_message"
]


class Capability(BaseModel):
    action: ActionName
    available: bool
    path: AccessPath | None = None
    note: str = ""


class ChannelStatus(BaseModel):
    channel: Channel
    connected: bool
    detail: str = ""
    capabilities: list[Capability]


class Post(BaseModel):
    id: str
    channel: Channel
    url: str | None = None
    caption: str | None = None
    created_at: datetime | None = None
    comment_count: int | None = None


class Comment(BaseModel):
    id: str
    channel: Channel
    post_ref: str
    author_handle: str
    author_name: str | None = None
    text: str
    created_at: datetime | None = None
    parent_id: str | None = None


class ActionKind(StrEnum):
    COMMENT_POST = "comment_post"
    REPLY_COMMENT = "reply_comment"
    SEND_MESSAGE = "send_message"  # DM / WhatsApp / email
    CRM_UPDATE = "crm_update"  # internal, tetap perlu persetujuan
    FOLLOWUP = "followup"  # pengingat terjadwal, perlu persetujuan
    MERGE = "merge"  # gabungkan dua profil (identitas ambigu), perlu persetujuan


EXTERNAL_KINDS = {ActionKind.COMMENT_POST, ActionKind.REPLY_COMMENT, ActionKind.SEND_MESSAGE}


class ActionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    # handoff: draf sudah disiapkan, menunggu pengguna mengirim sendiri
    AWAITING_MANUAL_SEND = "awaiting_manual_send"
    SENT_MANUALLY = "sent_manually"


class GuardNote(BaseModel):
    check: str
    status: Literal["pass", "warn", "block"]
    note: str = ""


class ProposedAction(BaseModel):
    """Usulan dari agen. Tidak pernah dieksekusi tanpa persetujuan manusia."""

    channel: Channel
    kind: ActionKind
    post_ref: str = Field(default="", description="URL atau ID post kanal")
    comment_ref: str | None = Field(
        default=None, description="ID komentar yang dibalas (wajib untuk reply_comment)"
    )
    text: str = Field(default="", max_length=2200)
    reason: str = Field(default="", description="Alasan agen, ditampilkan di UI")
    recipient: str | None = None
    due_at: datetime | None = None
    payload: dict = Field(default_factory=dict)
    guard: list[GuardNote] = Field(default_factory=list)
    public: bool = False
    lead_id: str | None = None
    event_id: str | None = None
    trace: dict | None = None

    @model_validator(mode="after")
    def _text_required(self) -> "ProposedAction":
        if self.kind not in (ActionKind.CRM_UPDATE, ActionKind.MERGE) and not self.text.strip():
            raise ValueError("text wajib diisi")
        return self


class Action(ProposedAction):
    id: str
    status: ActionStatus
    created_at: datetime
    decided_at: datetime | None = None
    edited: bool = False
    result_ref: str | None = None
    error: str | None = None
    reject_reason: str | None = None
    attempts: int = 0
    last_attempt_at: datetime | None = None
    next_retry_at: datetime | None = None
    delivery_status: Literal["sent", "delivered", "read", "failed"] | None = None
    delivery_at: datetime | None = None
    feedback: list[dict] = Field(default_factory=list)


class Sender(BaseModel):
    handle: str = ""
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class EventIn(BaseModel):
    """Pesan/komentar/email masuk, sudah dinormalisasi."""

    channel: Channel
    kind: Literal["comment", "dm", "email", "message"] = "message"
    external_id: str = Field(description="ID pesan di platform (untuk dedup)")
    sender: Sender = Field(default_factory=Sender)
    text: str = Field(min_length=1)
    ts: datetime | None = None
    post_ref: str | None = None
    comment_ref: str | None = None
    # Metadata khusus kanal (mis. Gmail: thread_id, rfc_message_id, subject)
    meta: dict = Field(default_factory=dict)


class Event(EventIn):
    id: str
    lead_id: str | None = None
    status: Literal["new", "processing", "analyzed", "review", "held", "agent_error"] = "new"
    triage: dict | None = None
    review_reason: str = ""
    trace: dict | None = None


class Lead(BaseModel):
    id: str
    name: str | None = None
    company: str | None = None
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    handles: list[str] = Field(default_factory=list, description="'kanal:handle' huruf kecil")
    stage: str = "baru"
    summary: str = ""
    score: int | None = None
    label: str | None = None
    score_reason: str = ""
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    estimated_value: int | None = None
    lost_reason: str = ""
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    identity_sources: dict[str, dict] = Field(default_factory=dict)


LEAD_STAGES = ("baru", "tertarik", "penawaran", "deal", "batal")
CLOSED_STAGES = ("deal", "batal")


def set_stage(lead: "Lead", stage: str, now: datetime) -> None:
    """Ubah tahap lead; tanggal closing diisi saat masuk Deal atau Batal dan dikosongkan bila dibuka lagi."""
    if stage != lead.stage:
        lead.closed_at = now if stage in CLOSED_STAGES else None
    lead.stage = stage


class KnowledgeProduct(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit_price: int = Field(ge=0, le=1_000_000_000)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    min_order: int = Field(default=1, ge=1, le=1_000_000)


class KnowledgeBase(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=100_000)
    products: list[KnowledgeProduct] = Field(default_factory=list, max_length=30)
    updated_at: datetime


class ChannelAgentConfig(BaseModel):
    knowledge_base_ids: list[str] = Field(default_factory=list, max_length=10)
    tone: Literal["friendly", "professional", "casual", "concise", "custom"] = "friendly"
    custom_tone: str = Field(default="", max_length=500)


class AppSettings(BaseModel):
    paused: bool = False
    disabled_channels: list[Channel] = Field(default_factory=list)
    dry_run: bool = False
    preferences: list[str] = Field(default_factory=list)
    rate_limit_per_hour: int = 30
    business_name: str = "Bisnis Anda"
    agent_channels: dict[str, ChannelAgentConfig] = Field(default_factory=dict)
    # Izin agen: manual (selalu tanya), hybrid (risiko rendah otomatis), auto (percaya penuh).
    autonomy: Literal["manual", "hybrid", "auto"] = "manual"
    auto_merge_threshold: float = Field(default=0.9, ge=0.5, le=1.0)


class AuditEntry(BaseModel):
    id: int
    ts: datetime
    action_id: str | None
    event: str
    detail: str
    actor: str = "system"
    channel: str | None = None
    lead_id: str | None = None
