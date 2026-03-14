"""JWT authentication middleware with dev bypass.

In development (DEBUG=true or no JWT_SECRET set), all requests are accepted
with a placeholder user. In production, JWTs are verified against JWT_SECRET.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)

_DEV_USER_ID = "dev-user-local"


@dataclass
class AuthUser:
    """Authenticated user extracted from JWT."""

    user_id: str
    email: str | None = None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    """Extract and verify the current user from the Authorization header.

    Dev mode (DEBUG=true or JWT_SECRET empty): returns a placeholder user.
    Production: decodes and validates the JWT.
    """
    if settings.DEBUG or not settings.JWT_SECRET:
        return AuthUser(user_id=_DEV_USER_ID, email="dev@localhost")

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return AuthUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email"),
    )
