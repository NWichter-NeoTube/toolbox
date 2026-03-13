"""Daemon loop — poll usage at regular intervals and log results."""

from __future__ import annotations

import signal
import time

import schedule
from rich.console import Console

from claude_usage.api_client import fetch_usage
from claude_usage.config import settings
from claude_usage.display import display_snapshot
from claude_usage.log_writer import write_log

console = Console()


def _check_alerts(snapshot) -> None:
    if snapshot.error:
        return
    if snapshot.five_hour.utilization >= settings.alert_five_hour_threshold:
        console.print(
            f"[bold red]ALERT: 5h session at {snapshot.five_hour.utilization:.1f}%"
            f" (threshold: {settings.alert_five_hour_threshold}%)[/bold red]"
        )
    if snapshot.seven_day.utilization >= settings.alert_seven_day_threshold:
        console.print(
            f"[bold red]ALERT: Weekly usage at {snapshot.seven_day.utilization:.1f}%"
            f" (threshold: {settings.alert_seven_day_threshold}%)[/bold red]"
        )


def run_monitor(interval: int, quiet: bool) -> None:
    """Main monitoring loop. Polls every `interval` seconds."""
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        console.print("\n[dim]Stopping monitor...[/dim]")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    def poll():
        snapshot = fetch_usage()
        write_log(snapshot)
        if not quiet:
            display_snapshot(snapshot)
        _check_alerts(snapshot)

    # Run immediately on start
    console.print(f"[bold]Claude Usage Monitor[/bold] — polling every {interval}s")
    console.print(f"[dim]Logs: {settings.log_dir.resolve()}[/dim]")
    console.print()
    poll()

    schedule.every(interval).seconds.do(poll)

    while running:
        schedule.run_pending()
        time.sleep(1)
