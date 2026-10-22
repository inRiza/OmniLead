from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends

from omnilead.api.deps import require_api_key
from omnilead.api.routes import router
from omnilead.api.scheduler_routes import router as scheduler_router
from omnilead.api.webhooks import router as webhook_router
from omnilead.config import get_settings
from omnilead.api.auth_routes import router as auth_router, check_origin
from omnilead.api.knowledge_routes import router as knowledge_router


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
        allow_credentials=True,
    )
    @app.middleware("http")
    async def protect_browser_requests(request, call_next):
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        try:
            if not request.url.path.startswith(("/webhooks/", "/scheduler/")):
                check_origin(request)
            response = await call_next(request)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(auth_router)
    app.include_router(knowledge_router, dependencies=[Depends(require_api_key)])
    app.include_router(router, dependencies=[Depends(require_api_key)])
    # Webhook dan Scheduler punya autentikasi sendiri (signature / token), bukan API key FE.
    app.include_router(webhook_router)
    app.include_router(scheduler_router)

    @app.on_event("startup")
    def demo_account() -> None:
        from omnilead.demo import ensure_demo_account

        ensure_demo_account(settings)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
