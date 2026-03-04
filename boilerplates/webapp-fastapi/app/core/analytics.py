"""PostHog server-side analytics client.

Wraps the PostHog Python SDK for the self-hosted instance used in the
toolbox stack.  All tracking helpers live here so the rest of the app
only needs to call thin wrappers.

DSGVO / GDPR note
------------------
Server-side PostHog does **not** set cookies — cookie handling is purely a
client-side concern.  This module is consent-aware: every public function
accepts a ``consent_given`` flag.  When consent has **not** been granted the
helpers will either skip the event entirely or strip PII from the properties
before sending an anonymous aggregate event — depending on the function.
"""

from __future__ import annotations

import logging
from typing import Any

import posthog

logger = logging.getLogger(__name__)

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


class AnalyticsClient:
    """Thin wrapper around the PostHog SDK.

    Call :meth:`initialize` once during application startup and
    :meth:`shutdown` during teardown to flush the event queue.
    """

    def __init__(self) -> None:
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, *, api_key: str, host: str) -> None:
        """Configure the PostHog SDK for the self-hosted instance."""
        if not api_key:
            logger.warning("PostHog API key is empty — analytics will be disabled")
            return
        posthog.api_key = api_key
        posthog.host = host
        posthog.debug = False
        posthog.on_error = self._on_error
        self._initialized = True
        logger.info("PostHog analytics client initialized (host=%s)", host)

    def shutdown(self) -> None:
        """Flush pending events and shut down the PostHog client."""
        if self._initialized:
            posthog.flush()
            posthog.shutdown()
            logger.info("PostHog analytics client shut down")
            self._initialized = False

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track_event(
        self,
        distinct_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
        *,
        consent_given: bool = True,
    ) -> None:
        """Track a single event.

        When *consent_given* is ``False`` the event is still recorded for
        aggregate metrics but under a generic anonymous ID with all PII
        stripped from *properties*.
        """
        if not self._initialized:
            return

        if consent_given:
            posthog.capture(distinct_id, event, properties=properties or {})
        else:
            # Anonymous aggregate tracking — no PII, generic ID.
            posthog.capture(
                "anonymous",
                event,
                properties=_strip_pii(properties),
            )

    def identify_user(
        self,
        distinct_id: str,
        properties: dict[str, Any] | None = None,
        *,
        consent_given: bool = True,
    ) -> None:
        """Identify a user with optional profile properties.

        Skipped entirely when consent has not been granted because
        identification is inherently PII.
        """
        if not self._initialized:
            return

        if not consent_given:
            logger.debug("identify_user skipped — no consent for distinct_id=%s", distinct_id)
            return

        posthog.identify(distinct_id, properties=properties or {})

    def get_feature_flag(
        self,
        flag_name: str,
        distinct_id: str,
        *,
        consent_given: bool = True,
    ) -> bool | str | None:
        """Evaluate a feature flag for *distinct_id* via PostHog.

        Returns the flag value (``True``/``False`` or a multivariate string)
        or ``None`` when PostHog is not available.
        """
        if not self._initialized:
            return None

        effective_id = distinct_id if consent_given else "anonymous"

        try:
            return posthog.get_feature_flag(flag_name, effective_id)
        except Exception:
            logger.exception("Failed to evaluate PostHog feature flag '%s'", flag_name)
            return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _on_error(error: Exception, items: Any) -> None:  # noqa: ARG004
        logger.error("PostHog error: %s", error)


# Module-level singleton used across the application.
analytics_client = AnalyticsClient()
