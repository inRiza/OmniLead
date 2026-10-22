"""Skema request/response khusus HTTP (yang tidak ada di models domain)."""

from typing import Literal

from pydantic import BaseModel, Field

from omnilead.models import Channel


class ApproveRequest(BaseModel):
    edited_text: str | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class PasteRequest(BaseModel):
    channel: Channel
    post_ref: str
    author_handle: str = ""
    text: str = Field(min_length=1)


class PauseRequest(BaseModel):
    paused: bool


class ChannelSettingsRequest(BaseModel):
    enabled: bool | None = None


class AppSettingsPatch(BaseModel):
    dry_run: bool | None = None
    rate_limit_per_hour: int | None = Field(default=None, ge=1, le=10_000)
    preferences: list[str] | None = None
    autonomy: Literal["manual", "hybrid", "auto"] | None = None


class LeadPatch(BaseModel):
    stage: Literal["baru", "tertarik", "penawaran", "deal", "batal"] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    estimated_value: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    lost_reason: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=20)


class PasteEventRequest(BaseModel):
    """Pesan dari Instagram, Facebook, WhatsApp, atau email yang ditempel pengguna."""

    channel: Channel
    text: str = Field(min_length=1)
    handle: str = ""
    name: str | None = None
    post_ref: str | None = None


class PasteImageRequest(BaseModel):
    channel: Channel
    image_base64: str = Field(min_length=1)
    mime_type: str = "image/png"
