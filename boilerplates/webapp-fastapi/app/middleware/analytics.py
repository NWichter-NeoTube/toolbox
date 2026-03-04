"""Middleware that tracks API requests in PostHog.

Every request that is **not** a health-check is recorded as a
``api_request`` event with method, path, status code, and duration.

Consent handling
----------------
The middleware reads the ``X-Consent`` header:

* ``"granted"`` — the event includes the user's ``distinct_id`` (taken
  from the ``X-User-ID`` header if present, otherwise from the request
  ID).
* Anything else (or absent) — the event is sent under the generic
  ``"anonymous"`` identity with PII stripped.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.analytics import analytics_client

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# Paths that should not be tracked.
_SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})

_CONSENT_HEADER = "x-consent"
_CONSENT_GRANTED = "granted"
_USER_ID_HEADER = "x-user-id"


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Record an ``api_request`` event in PostHog for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        consent_given = request.headers.get(_CONSENT_HEADER, "") == _CONSENT_GRANTED

        if consent_given:
            distinct_id = request.headers.get(
                _USER_ID_HEADER,
                getattr(request.state, "request_id", "unknown"),
            )
        else:
            distinct_id = "anonymous"

        properties: dict[str, object] = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        analytics_client.track_event(
            distinct_id=distinct_id,
            event="api_request",
            properties=properties,
            consent_given=consent_given,
        )

        return response
