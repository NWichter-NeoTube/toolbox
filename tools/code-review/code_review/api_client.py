"""Claude Messages API client using OAuth."""

from __future__ import annotations

import time

import httpx

from code_review.auth import AuthError, get_valid_token, refresh_token, load_credentials

MESSAGES_URL = "https://api.anthropic.com/v1/messages"


class APIError(Exception):
    pass


def call_claude(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 4096,
) -> tuple[str, int]:
    """Call Claude Messages API. Returns (response_text, tokens_used)."""
    token, _creds = get_valid_token()
    return _do_call(token, messages, model, system, max_tokens, retried=False)


def _do_call(
    token: str,
    messages: list[dict],
    model: str,
    system: str | None,
    max_tokens: int,
    retried: bool,
) -> tuple[str, int]:
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        body["system"] = system

    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "oauth-2025-04-20",
        "Content-Type": "application/json",
    }

    resp = httpx.post(MESSAGES_URL, json=body, headers=headers, timeout=120.0)

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("retry-after", "5"))
        time.sleep(retry_after)
        return _do_call(token, messages, model, system, max_tokens, retried=True)

    if resp.status_code == 401 and not retried:
        creds = load_credentials()
        new_creds = refresh_token(creds)
        return _do_call(
            new_creds["accessToken"], messages, model, system, max_tokens, retried=True
        )

    if resp.status_code != 200:
        raise APIError(f"Claude API error (HTTP {resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    text = data["content"][0]["text"]
    tokens = data.get("usage", {}).get("output_tokens", 0)
    return text, tokens
