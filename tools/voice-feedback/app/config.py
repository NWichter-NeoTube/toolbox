"""Application configuration via environment variables (pydantic-settings)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Voice-feedback service configuration.

    Values are read from environment variables or a ``.env`` file in the
    working directory.  Every variable can be overridden by setting it in the
    shell environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -- Whisper transcription -------------------------------------------------
    whisper_model: str = "base"
    """Whisper model size: tiny, base, small, medium, large-v3."""

    # -- PostHog ---------------------------------------------------------------
    posthog_api_key: str = ""
    """PostHog project API key (phx_...)."""

    posthog_host: str = "https://posthog.example.com"
    """PostHog instance URL."""

    # -- Analysis provider -----------------------------------------------------
    analysis_provider: str = "local"
    """'local' for rule-based keyword extraction, 'openai' for GPT-4 analysis."""

    openai_api_key: Optional[str] = None
    """OpenAI API key — only required when analysis_provider='openai'."""

    openai_model: str = "gpt-4o"
    """OpenAI model to use for transcript analysis."""

    # -- Storage ---------------------------------------------------------------
    upload_dir: Path = Path("./uploads")
    """Directory where uploaded audio files are stored."""

    output_dir: Path = Path("./output")
    """Directory where session JSON results are written."""

    # -- API server ------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # -- Helpers ---------------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create upload and output directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this everywhere.
settings = Settings()
