"""JSONL log file writer — one file per day."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claude_usage.config import settings
from claude_usage.models import LogEntry, UsageSnapshot


def _log_path(dt: datetime) -> Path:
    return settings.log_dir / f"usage_{dt.strftime('%Y-%m-%d')}.jsonl"


def write_log(snapshot: UsageSnapshot) -> Path:
    """Append a usage snapshot as a JSONL entry. Returns the log file path."""
    settings.ensure_dirs()
    entry = LogEntry.from_snapshot(snapshot)
    path = _log_path(entry.timestamp)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")
    return path


def read_logs(date: str | None = None, last: int = 20) -> list[LogEntry]:
    """Read log entries. If date is given (YYYY-MM-DD), read that day. Otherwise read latest."""
    settings.ensure_dirs()

    if date:
        path = settings.log_dir / f"usage_{date}.jsonl"
        if not path.exists():
            return []
        return _read_file(path, last)

    # Find latest log file
    files = sorted(settings.log_dir.glob("usage_*.jsonl"))
    if not files:
        return []
    return _read_file(files[-1], last)


def _read_file(path: Path, last: int) -> list[LogEntry]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines[-last:]:
        try:
            entries.append(LogEntry.model_validate_json(line))
        except Exception:
            continue
    return entries
