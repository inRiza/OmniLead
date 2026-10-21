"""Skema request/response khusus HTTP (yang tidak ada di models domain)."""

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


class PasteEventRequest(BaseModel):
    """Pesan dari kanal tanpa API (TikTok, LinkedIn DM, dll.) yang ditempel pengguna."""

    channel: Channel
    text: str = Field(min_length=1)
    handle: str = ""
    name: str | None = None
    post_ref: str | None = None


class PasteImageRequest(BaseModel):
    channel: Channel
    image_base64: str = Field(min_length=1)
    mime_type: str = "image/png"
