"""HTTP client for the Claude usage API endpoint."""

from __future__ import annotations

import httpx

from claude_usage.auth import AuthError, get_valid_token
from claude_usage.models import UsageSnapshot

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


def fetch_usage() -> UsageSnapshot:
    """Fetch current usage data from the Claude API."""
    try:
        token, creds = get_valid_token()
    except AuthError as e:
        return UsageSnapshot.from_error(str(e))

    try:
        resp = httpx.get(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

        if resp.status_code == 429:
            return UsageSnapshot.from_error("Rate limited (429). Will retry next poll.")

        resp.raise_for_status()
        data = resp.json()

        return UsageSnapshot.from_api(
            data,
            sub_type=creds.get("subscriptionType", ""),
            tier=creds.get("rateLimitTier", ""),
        )
    except httpx.HTTPStatusError as e:
        return UsageSnapshot.from_error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
    except httpx.RequestError as e:
        return UsageSnapshot.from_error(f"Request failed: {e}")
