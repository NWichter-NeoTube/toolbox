"""Log writer — delegates to SQLite storage backend."""

from __future__ import annotations

from pathlib import Path

from claude_usage.config import settings
from claude_usage.db import insert_entry, query_entries
from claude_usage.models import LogEntry, UsageSnapshot


def write_log(snapshot: UsageSnapshot) -> Path:
    """Write a usage snapshot to the database. Returns the database path."""
    settings.ensure_dirs()
    entry = LogEntry.from_snapshot(snapshot)
    return insert_entry(entry)


def read_logs(date: str | None = None, last: int = 20) -> list[LogEntry]:
    """Read log entries from the database."""
    settings.ensure_dirs()
    return query_entries(date=date, last=last)
