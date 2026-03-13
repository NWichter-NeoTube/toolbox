"""OAuth token management — read credentials from Claude Code, refresh when expired."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from code_review.config import settings

TOKEN_ENDPOINT = "https://platform.claude.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
REFRESH_BUFFER_MS = 10 * 60 * 1000


class AuthError(Exception):
    pass


def _load_raw(path: Path) -> dict:
    if not path.exists():
        raise AuthError(
            f"Credentials not found at {path}. Run 'claude /login' to authenticate."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _save_raw(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_credentials() -> dict:
    data = _load_raw(settings.credentials_path)
    creds = data.get("claudeAiOauth")
    if not creds:
        raise AuthError(
            "No 'claudeAiOauth' entry in credentials. Run 'claude /login' to authenticate."
        )
    return creds


def is_expired(creds: dict) -> bool:
    now_ms = int(time.time() * 1000)
    expires_at = creds.get("expiresAt", 0)
    return now_ms >= (expires_at - REFRESH_BUFFER_MS)


def refresh_token(creds: dict) -> dict:
    refresh_tok = creds.get("refreshToken")
    if not refresh_tok:
        raise AuthError("No refresh token available. Run 'claude /login' to re-authenticate.")

    resp = httpx.post(
        TOKEN_ENDPOINT,
        json={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": CLIENT_ID,
        },
        timeout=15.0,
    )
    if resp.status_code == 400:
        error_msg = resp.json().get("error_description", resp.text[:200])
        raise AuthError(
            f"Token refresh failed: {error_msg}\n"
            "Run 'claude /login' in a terminal to re-authenticate."
        )
    if resp.status_code != 200:
        raise AuthError(
            f"Token refresh failed (HTTP {resp.status_code}). "
            "Run 'claude /login' in a terminal to re-authenticate."
        )

    data = resp.json()
    new_creds = {
        "accessToken": data["access_token"],
        "refreshToken": data["refresh_token"],
        "expiresAt": int(time.time() * 1000) + data["expires_in"] * 1000,
        "scopes": data.get("scope", "").split(),
        "subscriptionType": creds.get("subscriptionType", ""),
        "rateLimitTier": creds.get("rateLimitTier", ""),
    }

    full = _load_raw(settings.credentials_path)
    full["claudeAiOauth"] = new_creds
    _save_raw(settings.credentials_path, full)

    return new_creds


def get_valid_token() -> tuple[str, dict]:
    """Return (access_token, credentials_dict) with a valid (non-expired) token."""
    creds = load_credentials()
    if is_expired(creds):
        creds = refresh_token(creds)
    return creds["accessToken"], creds
