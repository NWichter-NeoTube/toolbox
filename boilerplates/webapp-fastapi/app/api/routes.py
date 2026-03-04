"""Example API routes.

These routes demonstrate integration with the toolbox services
(PostHog analytics, Unleash feature flags, Sentry error tracking).
Replace or extend them to fit your application.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.core.analytics import analytics_client
from app.core.error_tracking import capture_exception, capture_message
from app.core.feature_flags import feature_flag_client

router = APIRouter(prefix="/api/v1", tags=["api"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EventPayload(BaseModel):
    """Body for the event ingestion endpoint."""

    event: str
    distinct_id: str = "anonymous"
    properties: dict[str, Any] = {}


class StatusResponse(BaseModel):
    """Response for the status endpoint."""

    app: str
    version: str
    debug: bool
    feature_flags: dict[str, bool | str | None]


class FlagResponse(BaseModel):
    """Response for the feature flag lookup endpoint."""

    flag: str
    enabled: bool
    variant: dict[str, Any]


class EventResponse(BaseModel):
    """Acknowledgement response for event ingestion."""

    accepted: bool
    event: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Return application status including sample feature flag evaluations."""
    from app.core.config import settings

    return StatusResponse(
        app="webapp-fastapi",
        version="0.1.0",
        debug=settings.DEBUG,
        feature_flags={
            "new-dashboard": feature_flag_client.is_enabled("new-dashboard"),
            "dark-mode": feature_flag_client.is_enabled("dark-mode"),
        },
    )


@router.post("/events", response_model=EventResponse)
async def ingest_event(
    payload: EventPayload,
    x_consent: str = Header(default=""),
) -> EventResponse:
    """Ingest a custom analytics event and forward it to PostHog."""
    consent_given = x_consent.lower() == "granted"

    analytics_client.track_event(
        distinct_id=payload.distinct_id,
        event=payload.event,
        properties=payload.properties,
        consent_given=consent_given,
    )

    # Also send a breadcrumb to Sentry for traceability.
    capture_message(f"Event ingested: {payload.event}", level="info")

    return EventResponse(accepted=True, event=payload.event)


@router.get("/flags/{flag_name}", response_model=FlagResponse)
async def check_flag(
    flag_name: str,
    distinct_id: str = "anonymous",
) -> FlagResponse:
    """Evaluate a feature flag via Unleash and return its status."""
    context = {"userId": distinct_id}

    try:
        enabled = feature_flag_client.is_enabled(flag_name, context=context)
        variant = feature_flag_client.get_variant(flag_name, context=context)
    except Exception as exc:
        capture_exception(exc)
        enabled = False
        variant = {}

    return FlagResponse(flag=flag_name, enabled=enabled, variant=variant)
