"""Pydantic models for usage data and log entries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class UsageWindow(BaseModel):
    """A single rate-limit window (5-hour or 7-day)."""

    utilization: float = Field(0.0, ge=0, le=100)
    resets_at: Optional[datetime] = None


class UsageSnapshot(BaseModel):
    """Point-in-time snapshot of Claude subscription usage."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    five_hour: UsageWindow = Field(default_factory=UsageWindow)
    seven_day: UsageWindow = Field(default_factory=UsageWindow)
    seven_day_opus: UsageWindow = Field(default_factory=UsageWindow)
    subscription_type: str = ""
    rate_limit_tier: str = ""
    error: Optional[str] = None

    @classmethod
    def from_api(cls, data: dict, sub_type: str = "", tier: str = "") -> UsageSnapshot:
        return cls(
            five_hour=UsageWindow(**(data.get("five_hour") or {})),
            seven_day=UsageWindow(**(data.get("seven_day") or {})),
            seven_day_opus=UsageWindow(**(data.get("seven_day_opus") or {})),
            subscription_type=sub_type,
            rate_limit_tier=tier,
        )

    @classmethod
    def from_error(cls, error: str) -> UsageSnapshot:
        return cls(error=error)


class LogEntry(BaseModel):
    """A single log entry written to the usage log file."""

    timestamp: datetime
    five_hour_pct: float
    five_hour_resets: Optional[str] = None
    seven_day_pct: float
    seven_day_resets: Optional[str] = None
    opus_pct: float
    opus_resets: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_snapshot(cls, snap: UsageSnapshot) -> LogEntry:
        return cls(
            timestamp=snap.timestamp,
            five_hour_pct=snap.five_hour.utilization,
            five_hour_resets=snap.five_hour.resets_at.isoformat() if snap.five_hour.resets_at else None,
            seven_day_pct=snap.seven_day.utilization,
            seven_day_resets=snap.seven_day.resets_at.isoformat() if snap.seven_day.resets_at else None,
            opus_pct=snap.seven_day_opus.utilization,
            opus_resets=snap.seven_day_opus.resets_at.isoformat() if snap.seven_day_opus.resets_at else None,
            error=snap.error,
        )
