"""FastAPI application entrypoint for the webapp-fastapi boilerplate."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.analytics import shutdown as analytics_shutdown
from app.core.config import settings
from app.core.error_tracking import init_error_tracking
from app.middleware.analytics import AnalyticsMiddleware
from app.middleware.request_id import RequestIDMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle.

    Startup: no external clients to initialize (Umami is stateless HTTP,
    feature flags are ENV-based).
    Shutdown: close the async HTTP client used for analytics.
    """
    # --- Startup ---
    yield

    # --- Shutdown ---
    await analytics_shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    init_error_tracking(
        dsn=settings.GLITCHTIP_DSN,
        environment="development" if settings.DEBUG else "production",
    )

    app = FastAPI(
        title="Webapp FastAPI",
        description="FastAPI boilerplate for the self-hosted SaaS toolbox stack",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # --- Middleware (order matters: outermost first) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AnalyticsMiddleware)

    # --- Routes ---
    app.include_router(api_router)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        """Health check endpoint for load balancers and orchestrators."""
        return {"status": "healthy"}

    return app


app = create_app()
