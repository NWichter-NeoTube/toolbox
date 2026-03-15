"""Background task helpers using FastAPI's built-in BackgroundTasks.

No external task queue needed. For heavier workloads, consider ARQ or Celery.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_email(to: str, subject: str, body: str) -> None:
    """Example background task: send an email via SMTP/Mailpit."""
    logger.info("Sending email to=%s subject=%s", to, subject)
    # TODO: Replace with actual SMTP client (e.g. aiosmtplib)
    # import aiosmtplib
    # await aiosmtplib.send(message, hostname="mailpit", port=1025)
    logger.info("Email sent to=%s", to)


async def log_event(event_name: str, data: dict[str, Any] | None = None) -> None:
    """Example background task: log an analytics/audit event."""
    logger.info("Event: %s data=%s", event_name, data)


async def cleanup_expired(model_name: str) -> None:
    """Example background task: clean up expired records."""
    logger.info("Cleaning up expired %s records", model_name)
    # TODO: Implement with database session
    # async with get_session() as session:
    #     await session.execute(delete(Model).where(Model.expires_at < utcnow()))
    #     await session.commit()
    logger.info("Cleanup complete for %s", model_name)
