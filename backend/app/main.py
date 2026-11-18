"""FastAPI application factory.

Wires the request-id middleware and domain-error handlers (M0-T2), CORS, the
health router, and Prometheus metrics. `uvicorn app.main:app` serves the module
-level ``app``; `make dev` runs it with reload.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.api.quiz import router as quiz_router
from app.api.skills import router as skills_router
from app.api.study import router as study_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import request_id_middleware


def create_app() -> FastAPI:
    """Build and configure the FastAPI app."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title="AI Prep Buddy", version="0.1.0")

    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(study_router)
    app.include_router(admin_router)
    app.include_router(quiz_router)
    app.include_router(skills_router)

    # /metrics + per-route latency histograms (hidden from the OpenAPI schema).
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
