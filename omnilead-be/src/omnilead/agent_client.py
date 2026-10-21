"""Klien HTTP ke service agen (omnilead-agent).

BE hanya mengirim konteks dan menerima USULAN. Service agen tidak memegang
token platform dan tidak punya jalur kirim.
"""

import time
from collections.abc import Callable

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


def google_id_token_provider(audience: str, ttl_s: int = 3000) -> Callable[[], str]:
    """Token identitas Google (Cloud Run IAM) untuk memanggil service agen yang tidak publik.

    Memakai Application Default Credentials / metadata server. Di-cache ~50 menit.
    """
    cache: dict = {"token": "", "exp": 0.0}

    def provider() -> str:
        if cache["token"] and time.time() < cache["exp"]:
            return cache["token"]
        import google.auth.transport.requests
        from google.oauth2 import id_token

        cache["token"] = id_token.fetch_id_token(google.auth.transport.requests.Request(), audience)
        cache["exp"] = time.time() + ttl_s
        return cache["token"]

    return provider


class AgentClient:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        token_provider: Callable[[], str] | None = None,
    ):
        self._token_provider = token_provider
        headers = {"X-API-Key": api_key} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def _auth(self) -> dict[str, str]:
        if not self._token_provider:
            return {}
        try:
            return {"Authorization": f"Bearer {self._token_provider()}"}
        except Exception as exc:  # kredensial Google tidak tersedia
            raise AgentUnavailable(f"Gagal mengambil token identitas: {type(exc).__name__}: {exc}") from exc

    def analyze(self, payload: dict) -> AgentResult:
        try:
            resp = self._http.post("/v1/analyze", json=payload, headers=self._auth())
            resp.raise_for_status()
            return AgentResult.model_validate(resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def extract(self, payload: dict) -> dict:
        """Ekstrak pengirim dan isi pesan dari screenshot (Gemini multimodal di service agen)."""
        try:
            resp = self._http.post("/v1/extract", json=payload, headers=self._auth())
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def content_ideas(self, payload: dict) -> dict:
        try:
            resp = self._http.post("/v1/content-ideas", json=payload, headers=self._auth())
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def health(self) -> dict:
        try:
            resp = self._http.get("/health", headers=self._auth())
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(str(exc)) from exc
