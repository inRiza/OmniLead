from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnilead.api.routes import router
from omnilead.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OmniLead Backend",
        version="0.1.0",
        summary="Connector Instagram & LinkedIn (API resmi) + handoff, "
        "antrean persetujuan, executor.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
