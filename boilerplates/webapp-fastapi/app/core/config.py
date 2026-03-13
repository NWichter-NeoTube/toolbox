"""Application configuration via pydantic-settings.

All settings are loaded from environment variables (or a .env file).
See .env.example for the full list of supported variables.
"""

from __future__ import annotations

import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the webapp-fastapi application.

    Values are populated from environment variables.  A ``.env`` file in the
    project root is loaded automatically when present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- Analytics (Umami) ---
    UMAMI_HOST: str = "https://track.sorevo.de"
    UMAMI_WEBSITE_ID: str = ""

    # --- Error Tracking (GlitchTip - Sentry-compatible) ---
    GLITCHTIP_DSN: str = ""

    # --- Feature Flags (ENV-based) ---
    # Access via settings.get_feature_flag("flag_name")

    # --- Database ---
    DATABASE_URL: str = "postgresql://toolbox:password@postgres:5432/toolbox"

    # --- Redis ---
    REDIS_URL: str = "redis://:password@redis:6379/0"

    # --- CORS ---
    CORS_ORIGINS: str = '["http://localhost:3000"]'

    # --- Debug ---
    DEBUG: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS JSON string into a Python list."""
        try:
            origins = json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            origins = [self.CORS_ORIGINS]
        if isinstance(origins, list):
            return [str(o) for o in origins]
        return [str(origins)]

    def get_feature_flag(self, name: str) -> bool:
        """Read feature flag from environment. Env var: FEATURE_{NAME}=true/false"""
        value = os.environ.get(f"FEATURE_{name.upper()}", "false")
        return value.lower() in ("true", "1", "yes")


settings = Settings()
