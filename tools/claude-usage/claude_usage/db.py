"""SQLite storage backend for usage logs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from claude_usage.config import settings
from claude_usage.models import LogEntry

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    five_hour_pct REAL NOT NULL,
    five_hour_resets TEXT,
    seven_day_pct REAL NOT NULL,
    seven_day_resets TEXT,
    opus_pct REAL NOT NULL,
    opus_resets TEXT,
    error TEXT
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_usage_log_timestamp ON usage_log(timestamp)
"""


def _db_path() -> Path:
    return settings.log_dir / "usage.db"


@contextmanager
def _connect():
    db = _db_path()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_INDEX)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_entry(entry: LogEntry) -> Path:
    """Insert a single log entry. Returns the database path."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO usage_log "
            "(timestamp, five_hour_pct, five_hour_resets, seven_day_pct, "
            "seven_day_resets, opus_pct, opus_resets, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.timestamp.isoformat(),
                entry.five_hour_pct,
                entry.five_hour_resets,
                entry.seven_day_pct,
                entry.seven_day_resets,
                entry.opus_pct,
                entry.opus_resets,
                entry.error,
            ),
        )
    return _db_path()


def query_entries(date: str | None = None, last: int = 20) -> list[LogEntry]:
    """Query log entries, optionally filtered by date (YYYY-MM-DD)."""
    with _connect() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM usage_log WHERE timestamp LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"{date}%", last),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM usage_log ORDER BY timestamp DESC LIMIT ?",
                (last,),
            ).fetchall()

    entries = []
    for row in reversed(rows):
        entries.append(LogEntry(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            five_hour_pct=row["five_hour_pct"],
            five_hour_resets=row["five_hour_resets"],
            seven_day_pct=row["seven_day_pct"],
            seven_day_resets=row["seven_day_resets"],
            opus_pct=row["opus_pct"],
            opus_resets=row["opus_resets"],
            error=row["error"],
        ))
    return entries


def query_stats(date: str | None = None) -> dict:
    """Return aggregate statistics (averages, peaks, count)."""
    with _connect() as conn:
        if date:
            row = conn.execute(
                "SELECT "
                "  AVG(five_hour_pct) as avg_5h, MAX(five_hour_pct) as max_5h, "
                "  AVG(seven_day_pct) as avg_7d, MAX(seven_day_pct) as max_7d, "
                "  AVG(opus_pct) as avg_opus, MAX(opus_pct) as max_opus, "
                "  COUNT(*) as count "
                "FROM usage_log WHERE error IS NULL AND timestamp LIKE ?",
                (f"{date}%",),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT "
                "  AVG(five_hour_pct) as avg_5h, MAX(five_hour_pct) as max_5h, "
                "  AVG(seven_day_pct) as avg_7d, MAX(seven_day_pct) as max_7d, "
                "  AVG(opus_pct) as avg_opus, MAX(opus_pct) as max_opus, "
                "  COUNT(*) as count "
                "FROM usage_log WHERE error IS NULL",
            ).fetchone()

    return {
        "avg_5h": row["avg_5h"] or 0.0,
        "max_5h": row["max_5h"] or 0.0,
        "avg_7d": row["avg_7d"] or 0.0,
        "max_7d": row["max_7d"] or 0.0,
        "avg_opus": row["avg_opus"] or 0.0,
        "max_opus": row["max_opus"] or 0.0,
        "count": row["count"],
    }


def migrate_jsonl(log_dir: Path) -> int:
    """Import existing JSONL log files into SQLite. Returns number of migrated entries."""
    files = sorted(log_dir.glob("usage_*.jsonl"))
    if not files:
        return 0

    count = 0
    with _connect() as conn:
        for f in files:
            lines = f.read_text(encoding="utf-8").strip().splitlines()
            batch = []
            for line in lines:
                try:
                    entry = LogEntry.model_validate_json(line)
                    batch.append((
                        entry.timestamp.isoformat(),
                        entry.five_hour_pct,
                        entry.five_hour_resets,
                        entry.seven_day_pct,
                        entry.seven_day_resets,
                        entry.opus_pct,
                        entry.opus_resets,
                        entry.error,
                    ))
                except Exception:
                    continue
            if batch:
                conn.executemany(
                    "INSERT INTO usage_log "
                    "(timestamp, five_hour_pct, five_hour_resets, seven_day_pct, "
                    "seven_day_resets, opus_pct, opus_resets, error) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                count += len(batch)

    return count
