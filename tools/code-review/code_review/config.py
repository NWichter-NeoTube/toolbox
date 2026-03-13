"""Configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODE_REVIEW_",
        extra="ignore",
    )

    # Auth
    credentials_path: Path = Path.home() / ".claude" / ".credentials.json"

    # Models
    review_model: str = "claude-sonnet-4-5"
    fix_model: str = "claude-sonnet-4-5"

    # Context
    context_lines: int = 50

    # Tokens
    max_tokens_review: int = 4096
    max_tokens_fix: int = 8192

    # Behavior
    auto_commit: bool = True

    # Knowledge base (global learning across projects)
    knowledge_dir: Path = Path.home() / ".code-review"

    @property
    def rules_path(self) -> Path:
        return self.knowledge_dir / "rules.json"

    @property
    def patterns_path(self) -> Path:
        return self.knowledge_dir / "patterns.json"

    def ensure_dirs(self) -> None:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
