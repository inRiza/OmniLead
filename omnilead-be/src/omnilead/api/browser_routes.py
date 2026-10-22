"""Authenticated workspace-scoped controls for the opt-in OpenClaw browser runtime."""

from typing import Literal

import hashlib
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr

from omnilead.api.deps import current_user, get_agent_client, ingest_for_workspace, store_for_workspace
from omnilead.browser_agent import BrowserConflict, manager
from omnilead.browser_login import AUTH_WORDS, SECRET_WORDS
from omnilead.config import get_settings
from omnilead.knowledge import build_context
from omnilead.models import Channel, EventIn, Sender

router = APIRouter(prefix="/browser-agent", tags=["browser-agent"])


class OpenBrowser(BaseModel):
    channel: Literal["instagram", "facebook", "whatsapp", "email"]


class BrowserTask(BaseModel):
    task: str = Field(min_length=3, max_length=2000, repr=False)
    account_label: str = Field(default="", max_length=100)
    allow_screenshot_to_model: bool = True


class BrowserChat(BaseModel):
    message: str = Field(min_length=1, max_length=2000, repr=False)
    channel: Literal["instagram", "facebook", "whatsapp", "email"] = "instagram"
    account_label: str = Field(default="", max_length=100)
    allow_screenshot_to_model: bool = True


class BrowserLogin(BaseModel):
    username: str = Field(default="", max_length=200)
    password: SecretStr = Field(default=SecretStr(""), repr=False)
    code: SecretStr = Field(default=SecretStr(""), repr=False)
    image_revision: int = Field(ge=1)
    confirmed: bool = False


class Approval(BaseModel):
    proposal_id: str = Field(min_length=1, max_length=64)


class ScreenshotConsent(BaseModel):
    allow_screenshot_to_model: bool = True


class ManualControl(BaseModel):
    operation: Literal["click", "type", "press", "inbox"]
    image_revision: int = Field(ge=1)
    x: int = Field(default=0, ge=0, le=1000)
    y: int = Field(default=0, ge=0, le=1000)
    text: str = Field(default="", max_length=4000, repr=False)
    key: Literal["Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "Backspace", "PageDown", "PageUp", "ControlOrMeta+A"] = "Tab"


class ImportMessage(BaseModel):
    extraction_id: str = Field(min_length=1, max_length=64)
    account_label: str = Field(min_length=1, max_length=100)
    handle: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=200)
    text: str = Field(min_length=1, max_length=10000)
    confirmed_incoming: bool = False


def scope(user=Depends(current_user)):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=403, detail="Agen browser memerlukan login pengguna.")
    if settings.demo_email and user["email"].lower() == settings.demo_email.lower():
        raise HTTPException(status_code=403, detail="Akun demo publik tidak mempunyai akses browser lokal.")
    return user["workspace_id"]


def available(workspace):
    if not get_settings().browser_enabled:
        raise HTTPException(status_code=409, detail="Agen browser belum diaktifkan pada server OmniLead.")
    actor = manager.get(workspace)
    if not actor or actor.snapshot()["status"] == "closed":
        raise HTTPException(status_code=409, detail="Buka browser untuk bisnis ini dahulu.")
    return actor


def state(workspace):
    actor = manager.get(workspace)
    return {"enabled": get_settings().browser_enabled, "session": actor.snapshot() if actor else None}


@router.get("")
def browser_state(workspace=Depends(scope)):
    return state(workspace)


@router.post("/open")
def open_browser(body: OpenBrowser, workspace=Depends(scope)):
    settings = get_settings()
    if not settings.browser_enabled:
        raise HTTPException(status_code=409, detail="Aktifkan OMNILEAD_BROWSER_ENABLED pada server OmniLead dahulu.")
    try:
        manager.open(workspace, body.channel, settings, get_agent_client(), store_for_workspace(workspace))
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/run")
def run_browser(body: BrowserTask, workspace=Depends(scope)):
    actor = available(workspace)
    if AUTH_WORDS.search(body.task):
        try:
            actor.request_login()
        except BrowserConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        return state(workspace)
    if not body.allow_screenshot_to_model:
        raise HTTPException(status_code=422, detail="Pembacaan layar sedang dimatikan. Aktifkan kembali di pengaturan sesi.")
    if not body.task.strip():
        raise HTTPException(status_code=422, detail="Tugas wajib diisi.")
    try:
        context = build_context(store_for_workspace(workspace), actor.channel, body.task)
        actor.run(body.task.strip(), "Akun yang sedang aktif pada browser", context)
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/login")
def login_browser(body: BrowserLogin, workspace=Depends(scope)):
    if not body.confirmed:
        raise HTTPException(status_code=422, detail="Konfirmasikan pengisian dan pengiriman formulir login.")
    if any(len(value) > 1000 or any(c in value for c in "\r\n\x00")
           for value in (body.username, body.password.get_secret_value(), body.code.get_secret_value())):
        raise HTTPException(status_code=422, detail="Input login tidak valid.")
    try:
        available(workspace).login(body)
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/chat")
def chat_browser(body: BrowserChat, workspace=Depends(scope)):
    settings = get_settings()
    if not settings.browser_enabled:
        raise HTTPException(status_code=409, detail="Agen browser belum diaktifkan pada server OmniLead.")
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Tuliskan pesan dahulu.")
    # Never retain text that might contain a password/OTP or send it to the planner.
    auth_request = bool(AUTH_WORDS.search(message))
    named_channel = re.search(r"\b(instagram|facebook|whatsapp|gmail|email)\b", message, re.I) if auth_request else None
    channel = ("email" if named_channel.group().lower() == "gmail" else named_channel.group().lower()) if named_channel else body.channel
    if SECRET_WORDS.search(message):
        message = "Bantu saya masuk ke akun kanal."
    actor = manager.get(workspace)
    try:
        if not actor or actor.snapshot()["status"] == "closed":
            actor = manager.open(workspace, channel, settings, get_agent_client(), store_for_workspace(workspace))
            actor.say("user", message)
            if not auth_request:
                actor.update(queued_task=message)
            return state(workspace)
        command = message.lower().strip(" .!")
        if command in {"stop", "berhenti", "hentikan", "batal"}:
            actor.stop()
        elif command in {"tutup", "tutup browser"}:
            actor.close()
        elif command in {"setuju", "setujui", "setujui langkah"}:
            pending = actor.snapshot()["pending"]
            if not pending:
                raise BrowserConflict("Belum ada langkah yang menunggu persetujuan.")
            actor.say("user", "Setujui langkah yang ditampilkan.")
            actor.approve(pending["id"])
        elif command in {"tolak", "jangan lanjut"}:
            actor.stop()
        elif command in {"perbarui layar", "cek layar", "cek login", "sudah login"}:
            actor.capture()
        elif auth_request:
            if actor.channel != channel:
                raise BrowserConflict("Tutup browser kanal saat ini dahulu, lalu minta login ke kanal yang baru.")
            if actor.snapshot()["status"] in {"error", "stopped"}:
                actor.reopen()
            else:
                actor.request_login()
        else:
            snapshot = actor.snapshot()
            if snapshot["status"] == "opening":
                raise BrowserConflict("Browser masih dibuka. Tunggu pesan kesiapan agen.")
            if snapshot["auth"]["stage"] != "none":
                if command in {"lanjut", "lanjutkan"}:
                    actor.capture()
                else:
                    actor.say("assistant", snapshot["auth"]["message"])
                return state(workspace)
            if not body.allow_screenshot_to_model:
                raise HTTPException(status_code=422, detail="Pembacaan layar sedang dimatikan. Aktifkan kembali di pengaturan sesi.")
            task = snapshot.get("queued_task") if command in {"lanjut", "lanjutkan"} else message
            if not task:
                raise BrowserConflict("Tuliskan tugas yang ingin Anda kerjakan.")
            account_label = "Akun yang sedang aktif pada browser"
            context = build_context(store_for_workspace(workspace), actor.channel, task)
            actor.run(task, account_label, context)
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/reopen")
def reopen_browser(workspace=Depends(scope)):
    try:
        available(workspace).reopen()
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/capture")
def capture_browser(workspace=Depends(scope)):
    try:
        available(workspace).capture()
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/approve")
def approve_browser(body: Approval, workspace=Depends(scope)):
    try:
        available(workspace).approve(body.proposal_id)
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/manual")
def manual_browser(body: ManualControl, workspace=Depends(scope)):
    if body.operation == "type" and (not body.text or any(c in body.text for c in "\r\n\x00")):
        raise HTTPException(status_code=422, detail="Input manual harus satu baris tanpa tombol kirim.")
    try:
        available(workspace).manual(body)
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/extract")
def extract_browser(body: ScreenshotConsent, workspace=Depends(scope)):
    if not body.allow_screenshot_to_model:
        raise HTTPException(status_code=422, detail="Izinkan screenshot dikirim ke model dahulu.")
    try:
        available(workspace).extract()
    except BrowserConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return state(workspace)


@router.post("/import")
def import_browser_message(body: ImportMessage, background: BackgroundTasks, workspace=Depends(scope)):
    actor = available(workspace)
    extracted = actor.snapshot().get("extracted")
    if not extracted or extracted["id"] != body.extraction_id:
        raise HTTPException(status_code=409, detail="Hasil pembacaan layar sudah berubah. Baca layar kembali.")
    if not body.confirmed_incoming or not body.text.strip() or not body.handle.strip() or not body.account_label.strip():
        raise HTTPException(status_code=422, detail="Konfirmasikan akun, pengirim, dan isi pesan masuk sebelum impor.")
    profile = hashlib.sha256(f"{workspace}:{actor.channel}:{body.account_label.strip().lower()}".encode()).hexdigest()
    event = EventIn(channel=Channel(actor.channel), kind="email" if actor.channel == "email" else "dm" if actor.channel in {"instagram", "facebook"} else "message",
        external_id="browser:" + body.extraction_id, sender=Sender(handle=body.handle.strip(), name=body.name.strip() or None),
        text=body.text.strip(), meta={"transport": "browser", "browser_page_url": extracted["page_url"],
            "browser_account_label": body.account_label.strip(), "business_account_id": "browser:" + profile})
    ingest = ingest_for_workspace(workspace)
    result, duplicate = ingest.ingest(event,
        defer_analysis=lambda created, is_new: background.add_task(ingest.process_created, created, is_new))
    return {"event_id": result.id, "duplicate": duplicate}


@router.post("/stop")
def stop_browser(workspace=Depends(scope)):
    available(workspace).stop()
    return state(workspace)


@router.post("/close")
def close_browser(workspace=Depends(scope)):
    available(workspace).close()
    return state(workspace)
