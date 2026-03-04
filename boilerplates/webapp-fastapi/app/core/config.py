"""Application configuration via pydantic-settings.

All settings are loaded from environment variables (or a .env file).
See .env.example for the full list of supported variables.
"""

from __future__ import annotations

import json

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

    # --- PostHog (self-hosted analytics) ---
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://posthog.example.com"

    # --- Sentry (self-hosted error tracking) ---
    SENTRY_DSN: str = ""

    # --- Unleash (self-hosted feature flags) ---
    UNLEASH_URL: str = "https://unleash.example.com/api"
    UNLEASH_API_TOKEN: str = ""
    UNLEASH_APP_NAME: str = "webapp-fastapi"

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


settings = Settings()
