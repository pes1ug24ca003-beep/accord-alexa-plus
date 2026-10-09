"""FastAPI application entrypoint for Accord backend core service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .api.routes import (
    agreements_router,
    assignments_router,
    constraints_router,
    demo_router,
    drift_router,
    households_router,
    interviews_router,
    monitoring_router,
)
from .config import settings
from .errors import ApiError, api_error_handler, unhandled_error_handler, validation_error_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="Accord backend core service (simulated integrations only).",
    )

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(households_router, prefix=settings.api_prefix)
    app.include_router(interviews_router, prefix=settings.api_prefix)
    app.include_router(constraints_router, prefix=settings.api_prefix)
    app.include_router(agreements_router, prefix=settings.api_prefix)
    app.include_router(assignments_router, prefix=settings.api_prefix)
    app.include_router(monitoring_router, prefix=settings.api_prefix)
    app.include_router(drift_router, prefix=settings.api_prefix)
    app.include_router(demo_router, prefix=settings.api_prefix)

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict:
        return {"status": "ok", "mode": "simulated"}

    return app


app = create_app()
