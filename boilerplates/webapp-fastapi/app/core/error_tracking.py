"""Sentry error tracking helpers for the self-hosted instance.

Provides a thin initialisation wrapper and convenience functions so that
the rest of the codebase does not import ``sentry_sdk`` directly.

PII scrubbing
-------------
The ``before_send`` hook inspects the event's request headers for an
``X-Consent`` header.  When the header is absent or not set to
``"granted"`` every user-related field is stripped from the event before
it leaves the process.  This keeps the Sentry instance DSGVO-compliant
even when users have not given consent.
"""

from __future__ import annotations

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

logger = logging.getLogger(__name__)

# Header that the analytics middleware and this module both inspect.
_CONSENT_HEADER = "x-consent"
_CONSENT_GRANTED = "granted"


def _before_send(
    event: dict[str, Any],
    hint: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any] | None:
    """Sentry before-send hook: strip PII when the user has not consented.

    The hook looks for the ``X-Consent`` header on the originating request.
    If consent was **not** given it removes user info, cookies, and
    query-string data from the event.
    """
    request_data: dict[str, Any] | None = event.get("request")
    consent_given = False

    if request_data:
        headers = request_data.get("headers", {})
        # Headers can come as a dict or as a list of pairs.
        if isinstance(headers, dict):
            consent_given = headers.get(_CONSENT_HEADER, "") == _CONSENT_GRANTED
        elif isinstance(headers, list):
            consent_given = any(
                k.lower() == _CONSENT_HEADER and v == _CONSENT_GRANTED
                for k, v in headers
            )

    if not consent_given:
        # Remove user context entirely.
        event.pop("user", None)
        if request_data:
            request_data.pop("cookies", None)
            request_data.pop("query_string", None)
            request_data.pop("data", None)
            # Scrub identifying headers but keep structural ones.
            if "headers" in request_data:
                request_data["headers"] = {}

    return event


def init_sentry(*, dsn: str, environment: str = "production") -> None:
    """Initialize the Sentry SDK with the self-hosted DSN.

    Silently skips initialization when *dsn* is empty so that local
    development works without a Sentry instance.
    """
    if not dsn:
        logger.warning("Sentry DSN is empty — error tracking will be disabled")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        before_send=_before_send,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry error tracking initialized (environment=%s)", environment)


def capture_message(msg: str, level: str = "info") -> None:
    """Send an informational message to Sentry."""
    sentry_sdk.capture_message(msg, level=level)


def capture_exception(exc: BaseException | None = None) -> None:
    """Report an exception to Sentry.

    When *exc* is ``None`` the current ``sys.exc_info()`` is used.
    """
    sentry_sdk.capture_exception(exc)
