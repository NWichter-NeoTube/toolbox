"""Middleware that attaches a unique request ID to every HTTP request.

The ID is:
* generated as a UUID-4 for each incoming request,
* stored on ``request.state.request_id`` so handlers can access it,
* returned to the caller in the ``X-Request-ID`` response header.

If the caller already supplies an ``X-Request-ID`` header the middleware
re-uses that value instead of generating a new one.  This is useful for
distributed tracing across services.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


_HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate a unique request ID."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = request.headers.get(_HEADER_NAME) or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[_HEADER_NAME] = request_id
        return response
