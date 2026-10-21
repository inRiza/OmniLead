"""Skema request/response khusus HTTP (yang tidak ada di models domain)."""

from pydantic import BaseModel, Field

from omnilead.models import ActionKind, Channel


class ProposeRequest(BaseModel):
    channel: Channel
    kind: ActionKind
    post_ref: str
    comment_ref: str | None = None
    text: str = Field(min_length=1, max_length=2200)
    reason: str = ""


class ApproveRequest(BaseModel):
    edited_text: str | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class PasteRequest(BaseModel):
    channel: Channel
    post_ref: str
    author_handle: str = ""
    text: str = Field(min_length=1)
