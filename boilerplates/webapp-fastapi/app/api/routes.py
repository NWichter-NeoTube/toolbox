"""Example API routes.

These routes demonstrate integration with the toolbox services
(Umami analytics, GlitchTip error tracking, ENV-based feature flags).
Replace or extend them to fit your application.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.core.analytics import track_event
from app.core.error_tracking import capture_exception, capture_message
from app.core.feature_flags import get_all_flags, is_enabled

router = APIRouter(prefix="/api/v1", tags=["api"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EventPayload(BaseModel):
    """Body for the event ingestion endpoint."""

    event: str
    properties: dict[str, Any] = {}


class StatusResponse(BaseModel):
    """Response for the status endpoint."""

    app: str
    version: str
    debug: bool
    feature_flags: dict[str, bool]


class FlagResponse(BaseModel):
    """Response for the feature flag lookup endpoint."""

    flag: str
    enabled: bool


class EventResponse(BaseModel):
    """Acknowledgement response for event ingestion."""

    accepted: bool
    event: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Return application status including active feature flags."""
    from app.core.config import settings

    return StatusResponse(
        app="webapp-fastapi",
        version="0.1.0",
        debug=settings.DEBUG,
        feature_flags=get_all_flags(),
    )


@router.post("/events", response_model=EventResponse)
async def ingest_event(
    payload: EventPayload,
    x_consent: str = Header(default=""),
) -> EventResponse:
    """Ingest a custom analytics event and forward it to Umami."""
    consent_given = x_consent.lower() == "granted"

    await track_event(
        name=payload.event,
        data=payload.properties,
        consent_given=consent_given,
    )

    # Also send a breadcrumb to GlitchTip for traceability.
    capture_message(f"Event ingested: {payload.event}", level="info")

    return EventResponse(accepted=True, event=payload.event)


@router.get("/flags/{flag_name}", response_model=FlagResponse)
async def check_flag(flag_name: str) -> FlagResponse:
    """Evaluate a feature flag from environment and return its status."""
    try:
        enabled = is_enabled(flag_name)
    except Exception as exc:
        capture_exception(exc)
        enabled = False

    return FlagResponse(flag=flag_name, enabled=enabled)
