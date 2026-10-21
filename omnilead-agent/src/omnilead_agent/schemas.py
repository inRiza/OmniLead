"""Kontrak request/response antara BE dan service agen.

Agen hanya menerima konteks dan mengembalikan USULAN. Tidak ada field atau
tool untuk mengirim ke platform.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Channel = Literal["instagram", "linkedin", "whatsapp", "email", "tiktok"]
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


class AnalyzeRequest(BaseModel):
    event: EventIn
    lead: LeadContext | None = None
    preferences: list[str] = Field(default_factory=list)
    # True = jendela balasan bebas terbuka. Kanal yang tidak tercantum dianggap terbuka.
    windows: dict[str, bool] = Field(default_factory=dict)
    # Nama/nomor pelanggan LAIN yang tidak boleh bocor ke draf.
    protected_terms: list[str] = Field(default_factory=list)


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
