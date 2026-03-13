"""Feature flags via environment variables.

A lightweight, dependency-free feature flag mechanism.  Each flag is
controlled by an environment variable with the ``FEATURE_`` prefix:

    FEATURE_DARK_MODE=true
    FEATURE_NEWSLETTER=false

This approach requires no external service -- flags are read directly
from the process environment.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def is_enabled(flag: str) -> bool:
    """Check if a feature flag is enabled via environment variable.

    Env var format: FEATURE_{FLAG_NAME}=true/false
    Example: FEATURE_DARK_MODE=true
    """
    env_key = f"FEATURE_{flag.upper()}"
    value = os.environ.get(env_key, "false")
    return value.lower() in ("true", "1", "yes")


def get_all_flags() -> dict[str, bool]:
    """Get all feature flags from environment."""
    flags = {}
    prefix = "FEATURE_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            flag_name = key[len(prefix):].lower()
            flags[flag_name] = value.lower() in ("true", "1", "yes")
    return flags
