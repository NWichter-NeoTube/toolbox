"""Middleware that tracks API requests via Umami.

Every request that is **not** a health-check is recorded as an
``api_request`` event with method, path, status code, and duration.

Consent handling
----------------
The middleware reads the ``X-Consent`` header:

* ``"granted"`` -- the event includes full request metadata.
* Anything else (or absent) -- PII is stripped from the event data.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.analytics import track_event

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# Paths that should not be tracked.
_SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})

_CONSENT_HEADER = "x-consent"
_CONSENT_GRANTED = "granted"


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Record an ``api_request`` event in Umami for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        consent_given = request.headers.get(_CONSENT_HEADER, "") == _CONSENT_GRANTED

        data: dict[str, object] = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        await track_event(
            name="api_request",
            data=data,
            url=request.url.path,
            consent_given=consent_given,
        )

        return response
