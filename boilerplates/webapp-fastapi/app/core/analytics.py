"""Analytics client using Umami HTTP API.

Wraps the Umami tracking API for the self-hosted instance used in the
toolbox stack.  All tracking helpers live here so the rest of the app
only needs to call thin wrappers.

DSGVO / GDPR note
------------------
Umami is privacy-focused by design -- it does not use cookies and does not
collect personal data.  This module still respects a ``consent_given`` flag
in public helpers: when consent has **not** been granted, PII properties are
stripped before sending the event.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

# Keys that are considered PII and will be stripped when consent is not given.
_PII_KEYS = frozenset({
    "email",
    "name",
    "first_name",
    "last_name",
    "phone",
    "ip",
    "ip_address",
    "user_agent",
    "username",
    "user_id",
})


def _strip_pii(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Return a shallow copy of *properties* with PII keys removed."""
    if not properties:
        return {}
    return {k: v for k, v in properties.items() if k.lower() not in _PII_KEYS}


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client


async def track_event(
    name: str,
    data: dict[str, Any] | None = None,
    url: str = "/",
    referrer: str = "",
    *,
    consent_given: bool = True,
) -> None:
    """Track an event via Umami API.

    When *consent_given* is ``False``, PII keys are stripped from *data*
    before sending the event.
    """
    if not settings.UMAMI_HOST or not settings.UMAMI_WEBSITE_ID:
        return

    effective_data = data if consent_given else _strip_pii(data)

    try:
        client = get_client()
        await client.post(
            f"{settings.UMAMI_HOST}/api/send",
            json={
                "payload": {
                    "website": settings.UMAMI_WEBSITE_ID,
                    "name": name,
                    "data": effective_data or {},
                    "url": url,
                    "referrer": referrer,
                },
                "type": "event",
            },
        )
    except Exception:
        logger.debug("Failed to send Umami event", exc_info=True)


async def track_pageview(url: str, referrer: str = "") -> None:
    """Track a pageview via Umami API."""
    if not settings.UMAMI_HOST or not settings.UMAMI_WEBSITE_ID:
        return

    try:
        client = get_client()
        await client.post(
            f"{settings.UMAMI_HOST}/api/send",
            json={
                "payload": {
                    "website": settings.UMAMI_WEBSITE_ID,
                    "url": url,
                    "referrer": referrer,
                },
                "type": "event",
            },
        )
    except Exception:
        logger.debug("Failed to send Umami pageview", exc_info=True)


async def shutdown() -> None:
    """Close the HTTP client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None
