"""Push analysis results to PostHog as custom events.

Creates two event types:
  - ``customer_feedback_session`` -- one per analysis session (overall data)
  - ``customer_feedback_item``    -- one per extracted feedback item

Optionally creates PostHog annotations for high-urgency items so they appear
on dashboards as markers.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models import AnalysisResult, Session, Urgency

logger = logging.getLogger(__name__)


def _get_posthog_client():
    """Return a configured PostHog client instance."""
    from posthog import Posthog  # type: ignore[import-untyped]

    if not settings.posthog_api_key:
        raise ValueError(
            "POSTHOG_API_KEY is required for PostHog sync. "
            "Set it in your environment or .env file."
        )

    return Posthog(
        api_key=settings.posthog_api_key,
        host=settings.posthog_host,
    )


def sync_to_posthog(
    analysis: AnalysisResult,
    session_id: str,
    distinct_id: Optional[str] = None,
    audio_file: Optional[str] = None,
) -> None:
    """Push analysis results to PostHog.

    Parameters
    ----------
    analysis:
        The completed analysis result.
    session_id:
        Unique session identifier (used to link events).
    distinct_id:
        PostHog distinct_id (customer identifier).  Falls back to the
        session_id if not provided.
    audio_file:
        Original audio file name (for reference).
    """
    client = _get_posthog_client()
    did = distinct_id or f"feedback-session-{session_id}"

    # -- Session-level event ---------------------------------------------------
    client.capture(
        distinct_id=did,
        event="customer_feedback_session",
        properties={
            "session_id": session_id,
            "source": "voice-feedback-tool",
            "sentiment": analysis.sentiment.value,
            "urgency": analysis.urgency.value,
            "topics": analysis.topics,
            "summary": analysis.summary,
            "suggestions": analysis.suggestions,
            "item_count": len(analysis.items),
            "provider": analysis.provider.value,
            "audio_file": audio_file or "",
            "feature_request_count": sum(
                1 for i in analysis.items if i.type.value == "feature_request"
            ),
            "bug_report_count": sum(
                1 for i in analysis.items if i.type.value == "bug_report"
            ),
            "pain_point_count": sum(
                1 for i in analysis.items if i.type.value == "pain_point"
            ),
            "praise_count": sum(
                1 for i in analysis.items if i.type.value == "praise"
            ),
            "churn_risk_count": sum(
                1 for i in analysis.items if i.type.value == "churn_risk"
            ),
        },
    )
    logger.info("Sent customer_feedback_session event for session %s", session_id)

    # -- Per-item events -------------------------------------------------------
    for idx, item in enumerate(analysis.items):
        client.capture(
            distinct_id=did,
            event="customer_feedback_item",
            properties={
                "session_id": session_id,
                "source": "voice-feedback-tool",
                "item_index": idx,
                "item_type": item.type.value,
                "item_text": item.text,
                "item_quote": item.quote,
                "item_urgency": item.urgency.value,
                "item_tags": item.tags,
            },
        )

    logger.info(
        "Sent %d customer_feedback_item events for session %s",
        len(analysis.items),
        session_id,
    )

    # -- Flush to ensure delivery ----------------------------------------------
    client.flush()
    logger.info("PostHog sync completed for session %s", session_id)


def sync_session(session: Session) -> None:
    """Convenience wrapper that syncs a full Session object."""
    if session.analysis is None:
        logger.warning("Session %s has no analysis — skipping PostHog sync.", session.id)
        return
    sync_to_posthog(
        analysis=session.analysis,
        session_id=session.id,
        audio_file=session.audio_file,
    )


def create_annotation(
    session_id: str,
    content: str,
    date_marker: Optional[datetime] = None,
) -> None:
    """Create a PostHog annotation for high-urgency feedback.

    Annotations appear as vertical markers on PostHog trend graphs, making
    it easy to correlate product metrics with customer feedback events.

    Note: This uses the PostHog REST API directly because the Python SDK
    does not expose annotation creation.
    """
    import httpx

    if not settings.posthog_api_key:
        logger.warning("Cannot create annotation — POSTHOG_API_KEY not set.")
        return

    url = f"{settings.posthog_host.rstrip('/')}/api/projects/@current/annotations/"
    marker_date = (date_marker or datetime.utcnow()).isoformat()

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.posthog_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "content": f"[voice-feedback] {content} (session: {session_id})",
            "date_marker": marker_date,
            "scope": "project",
        },
        timeout=10.0,
    )

    if response.is_success:
        logger.info("Created PostHog annotation for session %s", session_id)
    else:
        logger.warning(
            "Failed to create PostHog annotation (HTTP %d): %s",
            response.status_code,
            response.text[:200],
        )
