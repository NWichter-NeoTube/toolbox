"""Unleash feature flag client for the self-hosted instance.

Provides a resilient wrapper around the UnleashClient SDK.  When the
Unleash server is unreachable every helper degrades gracefully — features
default to *disabled* and variants return a safe empty dict.
"""

from __future__ import annotations

import logging
from typing import Any

from UnleashClient import UnleashClient

logger = logging.getLogger(__name__)


class FeatureFlagClient:
    """Wrapper around the Unleash Python SDK.

    Call :meth:`initialize` during application startup and :meth:`shutdown`
    on teardown.
    """

    def __init__(self) -> None:
        self._client: UnleashClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(
        self,
        *,
        url: str,
        api_token: str,
        app_name: str,
    ) -> None:
        """Create and start the Unleash client."""
        if not url or not api_token:
            logger.warning("Unleash URL or API token is empty — feature flags will be disabled")
            return

        try:
            self._client = UnleashClient(
                url=url,
                app_name=app_name,
                custom_headers={"Authorization": api_token},
            )
            self._client.initialize_client()
            logger.info("Unleash feature flag client initialized (url=%s, app=%s)", url, app_name)
        except Exception:
            logger.exception("Failed to initialize Unleash client")
            self._client = None

    def shutdown(self) -> None:
        """Destroy the Unleash client."""
        if self._client is not None:
            try:
                self._client.destroy()
            except Exception:
                logger.exception("Error while shutting down Unleash client")
            finally:
                self._client = None
                logger.info("Unleash feature flag client shut down")

    # ------------------------------------------------------------------
    # Feature flag helpers
    # ------------------------------------------------------------------

    def is_enabled(
        self,
        feature_name: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check whether *feature_name* is enabled.

        Returns ``False`` when the Unleash client is unavailable so that
        features degrade safely.
        """
        if self._client is None:
            logger.debug(
                "Unleash client not available — defaulting '%s' to disabled",
                feature_name,
            )
            return False

        try:
            return self._client.is_enabled(feature_name, context or {})
        except Exception:
            logger.exception("Error evaluating feature flag '%s'", feature_name)
            return False

    def get_variant(
        self,
        feature_name: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the variant for *feature_name*.

        Returns an empty dict when Unleash is unavailable.
        """
        if self._client is None:
            logger.debug(
                "Unleash client not available — returning empty variant for '%s'",
                feature_name,
            )
            return {}

        try:
            variant = self._client.get_variant(feature_name, context or {})
            return variant if isinstance(variant, dict) else {}
        except Exception:
            logger.exception("Error fetching variant for '%s'", feature_name)
            return {}


# Module-level singleton used across the application.
feature_flag_client = FeatureFlagClient()
