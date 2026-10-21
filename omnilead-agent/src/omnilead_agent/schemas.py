"""Kontrak request/response antara BE dan service agen.

Agen hanya menerima konteks dan mengembalikan USULAN. Tidak ada field atau
tool untuk mengirim ke platform.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Channel = Literal["instagram", "facebook", "whatsapp", "email"]
EventKind = Literal["comment", "dm", "email", "message"]
ProposalKind = Literal[
    "comment_post", "reply_comment", "send_message", "crm_update", "followup"
]


class Sender(BaseModel):
    handle: str = ""
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class EventIn(BaseModel):
    id: str
    channel: Channel
    kind: EventKind = "message"
    sender: Sender = Field(default_factory=Sender)
    text: str
    ts: datetime | None = None
    post_ref: str | None = None
    comment_ref: str | None = None


class TimelineItem(BaseModel):
    ts: datetime | None = None
    channel: Channel
    direction: Literal["in", "out"] = "in"
    text: str


class LeadContext(BaseModel):
    id: str
    name: str | None = None
    company: str | None = None
    stage: str = "baru"
    summary: str = ""
    timeline: list[TimelineItem] = Field(default_factory=list)


class KnowledgeDocument(BaseModel):
    id: str = Field(max_length=100)
    name: str = Field(max_length=100)
    content: str = Field(max_length=12_000)


class BusinessProduct(BaseModel):
    id: str = Field(max_length=100)
    name: str = Field(min_length=1, max_length=120)
    unit_price: int = Field(ge=0, le=1_000_000_000)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    min_order: int = Field(default=1, ge=1, le=1_000_000)


class BusinessContext(BaseModel):
    business: str = Field(max_length=100)
    channel: Channel
    tone: Literal["friendly", "professional", "casual", "concise", "custom"] = "friendly"
    tone_instruction: str = Field(default="", max_length=500)
    documents: list[KnowledgeDocument] = Field(default_factory=list, max_length=10)
    products: list[BusinessProduct] = Field(default_factory=list, max_length=300)


class AnalyzeRequest(BaseModel):
    event: EventIn
    lead: LeadContext | None = None
    preferences: list[str] = Field(default_factory=list)
    # True = jendela balasan bebas terbuka. Kanal yang tidak tercantum dianggap terbuka.
    windows: dict[str, bool] = Field(default_factory=dict)
    # Nama/nomor pelanggan LAIN yang tidak boleh bocor ke draf.
    protected_terms: list[str] = Field(default_factory=list)
    business_context: BusinessContext | None = None

    @model_validator(mode="after")
    def context_matches_channel(self):
        if self.business_context and self.business_context.channel != self.event.channel:
            raise ValueError("Konteks bisnis tidak sesuai kanal event")
        return self


class TriageResult(BaseModel):
    intents: list[str]
    urgency: Literal["tinggi", "sedang", "rendah"]
    urgency_reason: str
    sentiment: Literal["positif", "netral", "negatif"]
    entities: dict[str, object] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    language: str = "id-informal"


class GuardNote(BaseModel):
    check: str
    status: Literal["pass", "warn", "block"]
    note: str = ""


class Proposal(BaseModel):
    kind: ProposalKind
    channel: Channel
    post_ref: str = ""
    comment_ref: str | None = None
    recipient: str | None = None
    text: str = ""
    reason: str = ""
    due_at: datetime | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    guard: list[GuardNote] = Field(default_factory=list)
    # Tag internal untuk Guard: apakah teks ini tampil publik.
    public: bool = False


class LeadScore(BaseModel):
    score: int
    label: Literal["Hot", "Warm", "Cold"]
    reasons: list[str]


class CrmUpdate(BaseModel):
    stage: str
    summary: str
    score: int
    label: str
    score_reason: str


class TraceStep(BaseModel):
    n: int
    tool: str
    input: dict[str, object] = Field(default_factory=dict)
    result: str = ""


class Trace(BaseModel):
    goal: str
    plan: list[str] = Field(default_factory=list)
    steps: list[TraceStep] = Field(default_factory=list)
    guard_summary: str = ""
    status: str = ""
    revisions: int = 0
    activity: list[dict] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    event_id: str
    triage: TriageResult
    score: LeadScore | None = None
    crm: CrmUpdate | None = None
    proposals: list[Proposal] = Field(default_factory=list)
    flagged_for_review: bool = False
    review_reason: str = ""
    guard: list[GuardNote] = Field(default_factory=list)
    trace: Trace
