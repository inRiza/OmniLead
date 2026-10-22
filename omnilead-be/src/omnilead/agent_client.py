"""Klien HTTP ke service agen (omnilead-agent).

BE hanya mengirim konteks dan menerima USULAN. Service agen tidak memegang
token platform dan tidak punya jalur kirim.
"""

import json
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
        self._timeout = timeout
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

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def analyze(self, payload: dict) -> AgentResult:
        try:
            resp = self._http.post("/v1/analyze", json=payload, headers=self._auth())
            resp.raise_for_status()
            return AgentResult.model_validate(resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def analyze_stream(self, payload: dict, on_progress: Callable[[dict], None]) -> AgentResult:
        started = time.monotonic()
        try:
            with self._http.stream("POST", "/v1/analyze/stream", json=payload, headers=self._auth()) as response:
                # Allow a rolling upgrade when the agent is still on the older API.
                if response.status_code in (404, 405):
                    return self.analyze(payload)
                response.raise_for_status()
                for line in response.iter_lines():
                    if time.monotonic() - started > self._timeout:
                        raise AgentUnavailable("Analisis melewati batas waktu. Coba proses ulang pesan.")
                    if not line:
                        continue
                    item = json.loads(line)
                    if item.get("type") == "progress":
                        on_progress(item["data"])
                    elif item.get("type") == "result":
                        return AgentResult.model_validate(item["data"])
                    elif item.get("type") == "error":
                        raise AgentUnavailable("Analisis agen gagal. Coba proses ulang pesan.")
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise AgentUnavailable("Koneksi ke agen terputus atau hasil analisis tidak valid.") from None
        raise AgentUnavailable("Koneksi agen berakhir sebelum hasil analisis diterima.")

    def extract(self, payload: dict) -> dict:
        """Ekstrak pengirim dan isi pesan dari screenshot (Gemini multimodal di service agen)."""
        try:
            resp = self._http.post("/v1/extract", json=payload, headers=self._auth())
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def chat_step(self, payload: dict) -> dict:
        """Satu langkah chat pemilik: agen memilih tool atau menjawab (tool dijalankan BE)."""
        try:
            resp = self._http.post("/v1/chat/step", json=payload, headers=self._auth())
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def chat_step_stream(self, payload: dict):
        try:
            with self._http.stream("POST", "/v1/chat/stream", json=payload, headers=self._auth()) as resp:
                if resp.status_code in (404, 405):
                    yield {"type": "decision", "data": self.chat_step(payload)}
                    return
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.strip():
                        event = json.loads(line)
                        if event.get("type") == "error":
                            raise AgentUnavailable(event.get("message", "Model chat gagal"))
                        yield event
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
