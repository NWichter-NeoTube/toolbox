"""Rich console output for usage snapshots and history."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from claude_usage.models import LogEntry, UsageSnapshot

console = Console()


def _bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    empty = width - filled
    return "#" * filled + "-" * empty


def _pct_color(pct: float) -> str:
    if pct >= 80:
        return "red"
    if pct >= 50:
        return "yellow"
    return "green"


def _format_reset(dt: datetime | None) -> str:
    if not dt:
        return "--"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - now
    if delta.total_seconds() <= 0:
        return "now"
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    if hours > 24:
        return dt.strftime("%Y-%m-%d %H:%M")
    return f"{hours}h {minutes}m"


def display_snapshot(snapshot: UsageSnapshot) -> None:
    """Print a usage snapshot as a Rich panel."""
    if snapshot.error:
        console.print(f"[red]Error: {snapshot.error}[/red]")
        return

    ts = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = []

    # 5-hour session
    c5 = _pct_color(snapshot.five_hour.utilization)
    lines.append(
        f"  5h Session     [{c5}]{_bar(snapshot.five_hour.utilization)}[/{c5}]"
        f"  [{c5}]{snapshot.five_hour.utilization:5.1f}%[/{c5}]"
        f"    Reset: {_format_reset(snapshot.five_hour.resets_at)}"
    )

    # 7-day
    c7 = _pct_color(snapshot.seven_day.utilization)
    lines.append(
        f"  Weekly         [{c7}]{_bar(snapshot.seven_day.utilization)}[/{c7}]"
        f"  [{c7}]{snapshot.seven_day.utilization:5.1f}%[/{c7}]"
        f"    Reset: {_format_reset(snapshot.seven_day.resets_at)}"
    )

    # Opus
    co = _pct_color(snapshot.seven_day_opus.utilization)
    lines.append(
        f"  Weekly (Opus)  [{co}]{_bar(snapshot.seven_day_opus.utilization)}[/{co}]"
        f"  [{co}]{snapshot.seven_day_opus.utilization:5.1f}%[/{co}]"
        f"    Reset: {_format_reset(snapshot.seven_day_opus.resets_at)}"
    )

    if snapshot.subscription_type:
        lines.append(f"\n  Plan: {snapshot.subscription_type}   Tier: {snapshot.rate_limit_tier}")

    body = "\n".join(lines)
    console.print(Panel(body, title=f"Claude Usage  {ts}", border_style="blue"))


def display_history(entries: list[LogEntry]) -> None:
    """Print historical log entries as a Rich table."""
    if not entries:
        console.print("[dim]No log entries found.[/dim]")
        return

    table = Table(title="Usage History", show_lines=False)
    table.add_column("Timestamp", style="cyan", width=20)
    table.add_column("5h %", justify="right", width=7)
    table.add_column("Weekly %", justify="right", width=9)
    table.add_column("Opus %", justify="right", width=7)
    table.add_column("Error", width=30)

    for e in entries:
        ts = e.timestamp.strftime("%H:%M:%S") if entries[0].timestamp.date() == e.timestamp.date() else e.timestamp.strftime("%Y-%m-%d %H:%M")
        c5 = _pct_color(e.five_hour_pct)
        c7 = _pct_color(e.seven_day_pct)
        co = _pct_color(e.opus_pct)
        table.add_row(
            ts,
            f"[{c5}]{e.five_hour_pct:.1f}[/{c5}]",
            f"[{c7}]{e.seven_day_pct:.1f}[/{c7}]",
            f"[{co}]{e.opus_pct:.1f}[/{co}]",
            e.error or "",
        )

    console.print(table)


def display_stats(stats: dict, date: str | None = None) -> None:
    """Print aggregate usage statistics."""
    if stats["count"] == 0:
        console.print("[dim]No data available.[/dim]")
        return

    title = f"Usage Stats  {date}" if date else "Usage Stats  (all time)"

    lines = [
        f"  {'':16s} {'Avg':>8s}  {'Peak':>8s}",
        f"  {'5h Session':16s} {stats['avg_5h']:7.1f}%  {stats['max_5h']:7.1f}%",
        f"  {'Weekly':16s} {stats['avg_7d']:7.1f}%  {stats['max_7d']:7.1f}%",
        f"  {'Weekly (Opus)':16s} {stats['avg_opus']:7.1f}%  {stats['max_opus']:7.1f}%",
        f"",
        f"  Data points: {stats['count']}",
    ]

    body = "\n".join(lines)
    console.print(Panel(body, title=title, border_style="blue"))
