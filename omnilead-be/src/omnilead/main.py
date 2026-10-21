from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends

from omnilead.api.deps import require_api_key
from omnilead.api.routes import router
from omnilead.api.scheduler_routes import router as scheduler_router
from omnilead.api.webhooks import router as webhook_router
from omnilead.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OmniLead Backend",
        version="0.2.0",
        summary="Ingest event, antrean persetujuan, executor, connector, "
        "dan klien ke service agen (omnilead-agent).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, dependencies=[Depends(require_api_key)])
    # Webhook dan Scheduler punya autentikasi sendiri (signature / token), bukan API key FE.
    app.include_router(webhook_router)
    app.include_router(scheduler_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
