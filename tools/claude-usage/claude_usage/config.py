"""Application configuration via environment variables (pydantic-settings)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLAUDE_USAGE_",
    )

    # Polling
    interval_seconds: int = 300

    # Credentials
    credentials_path: Path = Path.home() / ".claude" / ".credentials.json"

    # Output
    log_dir: Path = Path("./logs")

    @property
    def db_path(self) -> Path:
        return self.log_dir / "usage.db"

    # Display
    quiet: bool = False

    # Alert thresholds (percentage)
    alert_five_hour_threshold: float = 80.0
    alert_seven_day_threshold: float = 70.0

    def ensure_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton
settings = Settings()
