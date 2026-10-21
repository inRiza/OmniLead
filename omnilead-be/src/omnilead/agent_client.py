"""Klien HTTP ke service agen (omnilead-agent).

BE hanya mengirim konteks dan menerima USULAN. Service agen tidak memegang
token platform dan tidak punya jalur kirim.
"""

import httpx
from pydantic import BaseModel, Field

from omnilead.models import GuardNote


class AgentUnavailable(Exception):
    """Service agen tidak terjangkau atau mengembalikan respons tidak sah."""


class AgentProposal(BaseModel):
    model_config = {"extra": "ignore"}

    kind: str
    channel: str
    post_ref: str = ""
    comment_ref: str | None = None
    recipient: str | None = None
    text: str = ""
    reason: str = ""
    due_at: str | None = None
    payload: dict = Field(default_factory=dict)
    guard: list[GuardNote] = Field(default_factory=list)
    public: bool = False


class AgentResult(BaseModel):
    model_config = {"extra": "ignore"}

    triage: dict = Field(default_factory=dict)
    score: dict | None = None
    crm: dict | None = None
    proposals: list[AgentProposal] = Field(default_factory=list)
    flagged_for_review: bool = False
    review_reason: str = ""
    guard: list[GuardNote] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)


class AgentClient:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ):
        headers = {"X-API-Key": api_key} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def analyze(self, payload: dict) -> AgentResult:
        try:
            resp = self._http.post("/v1/analyze", json=payload)
            resp.raise_for_status()
            return AgentResult.model_validate(resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def extract(self, payload: dict) -> dict:
        """Ekstrak pengirim dan isi pesan dari screenshot (Gemini multimodal di service agen)."""
        try:
            resp = self._http.post("/v1/extract", json=payload)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def health(self) -> dict:
        try:
            resp = self._http.get("/health")
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(str(exc)) from exc
