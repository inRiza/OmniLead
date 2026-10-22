"""HTTP service agen. Dipanggil oleh BE, bukan oleh FE.

  GET  /health
  POST /v1/analyze   AnalyzeRequest -> AnalyzeResponse (hanya usulan)

Tidak ada endpoint yang mengirim pesan ke platform.
"""

import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

from omnilead_agent.content_ideas import ContentIdeasRequest, ContentIdeasResponse, suggest
from omnilead_agent.extract import (
    ExtractResult,
    ExtractUnavailable,
    Extractor,
    GeminiExtractor,
    decode_image,
)
from omnilead_agent.pipeline import analyze, engine_name
from omnilead_agent.schemas import AnalyzeRequest, AnalyzeResponse
from omnilead_agent.progress import run_observed, stream_analysis
from omnilead_agent.browser import BrowserAction, BrowserPlanRequest, propose_browser_action


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("OMNILEAD_AGENT_API_KEY", "")
    if not expected:
        return  # dev: autentikasi mati
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="API key salah")


class ExtractRequest(BaseModel):
    image_base64: str
    mime_type: str = "image/png"
    channel: str = ""


def get_extractor() -> Extractor:
    return GeminiExtractor()


def create_app() -> FastAPI:
    app = FastAPI(
        title="OmniLead Agent",
        version="0.1.0",
        summary="Triage, orchestrator, dan guard. Hanya mengusulkan aksi.",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "engine": engine_name(), "can_send": False}

    @app.post("/v1/analyze", response_model=AnalyzeResponse, dependencies=[Depends(require_key)])
    def analyze_event(req: AnalyzeRequest) -> AnalyzeResponse:
        return run_observed(analyze, req)

    @app.post("/v1/browser/plan", response_model=BrowserAction, dependencies=[Depends(require_key)])
    def browser_plan(req: BrowserPlanRequest) -> BrowserAction:
        try:
            return propose_browser_action(req)
        except Exception:
            raise HTTPException(status_code=503,
                detail="Planner visual belum tersedia. Periksa model dan kredensial Gemini pada service agen.") from None

    @app.post("/v1/analyze/stream", dependencies=[Depends(require_key)])
    def analyze_stream(req: AnalyzeRequest):
        return StreamingResponse(stream_analysis(analyze, req), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.post("/v1/extract", response_model=ExtractResult, dependencies=[Depends(require_key)])
    def extract_message(
        req: ExtractRequest, extractor: Extractor = Depends(get_extractor)
    ) -> ExtractResult:
        """Baca pesan dari screenshot (kanal tanpa API). Hanya mengembalikan teks."""
        if not req.mime_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Hanya gambar yang didukung")
        try:
            image = decode_image(req.image_base64)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        try:
            return extractor.extract(image, req.mime_type, req.channel)
        except ExtractUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @app.post(
        "/v1/content-ideas", response_model=ContentIdeasResponse, dependencies=[Depends(require_key)]
    )
    def content_ideas(req: ContentIdeasRequest) -> ContentIdeasResponse:
        """Ide konten (draf saja) dari pertanyaan pelanggan yang sering muncul."""
        return suggest(req.messages)

    return app


app = create_app()
