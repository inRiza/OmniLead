"""Model data yang sama untuk semua kanal.

Agen dan FE hanya melihat bentuk ini, tidak peduli connector di baliknya.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Channel(StrEnum):
    INSTAGRAM = "instagram"


# Jalur akses yang diakui. Hanya resmi atau handoff manual.
#   official_api : panggil API resmi platform.
#   handoff      : tidak ada API; manusia menempel pesan masuk dan mengirim sendiri.
AccessPath = Literal["official_api", "handoff"]

ActionName = Literal["list_posts", "read_comments", "post_comment", "reply_comment"]


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


class ActionStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    # handoff: draf sudah disiapkan, menunggu pengguna mengirim sendiri
    AWAITING_MANUAL_SEND = "awaiting_manual_send"
    SENT_MANUALLY = "sent_manually"


class ProposedAction(BaseModel):
    """Usulan dari agen. Tidak pernah dieksekusi tanpa persetujuan manusia."""

    channel: Channel
    kind: ActionKind
    post_ref: str = Field(description="URL atau ID post kanal")
    comment_ref: str | None = Field(
        default=None, description="ID komentar yang dibalas (wajib untuk reply_comment)"
    )
    text: str = Field(min_length=1, max_length=2200)
    reason: str = Field(default="", description="Alasan agen, ditampilkan di UI")


class Action(ProposedAction):
    id: str
    status: ActionStatus
    created_at: datetime
    decided_at: datetime | None = None
    edited: bool = False
    result_ref: str | None = None
    error: str | None = None
    reject_reason: str | None = None


class AuditEntry(BaseModel):
    id: int
    ts: datetime
    action_id: str | None
    event: str
    detail: str
