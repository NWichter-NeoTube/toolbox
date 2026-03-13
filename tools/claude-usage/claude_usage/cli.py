"""Click CLI for claude-usage monitor.

Commands
--------
claude-usage check               Check usage once and display
claude-usage watch                Daemon mode — poll every 5 min
claude-usage history              View historical log entries
"""

from __future__ import annotations

import click

from claude_usage.config import settings
from claude_usage.display import console


@click.group()
@click.version_option(version="0.1.0", prog_name="claude-usage")
def cli():
    """Monitor Claude subscription usage (5-hour session + weekly limits)."""
    settings.ensure_dirs()


@cli.command()
@click.option("--log/--no-log", default=True, help="Write result to log file.")
def check(log: bool):
    """Check current usage once and display results."""
    from claude_usage.api_client import fetch_usage
    from claude_usage.display import display_snapshot
    from claude_usage.log_writer import write_log

    snapshot = fetch_usage()
    display_snapshot(snapshot)

    if log:
        path = write_log(snapshot)
        console.print(f"[dim]Logged to {path}[/dim]")


@cli.command()
@click.option("--interval", "-i", default=None, type=int, help="Poll interval in seconds (default: 300).")
@click.option("--quiet", "-q", is_flag=True, help="Suppress console output, only log to file.")
def watch(interval: int | None, quiet: bool):
    """Start continuous monitoring (polls every 5 minutes by default)."""
    from claude_usage.monitor import run_monitor

    run_monitor(
        interval=interval or settings.interval_seconds,
        quiet=quiet,
    )


@cli.command()
@click.option("--date", "-d", default=None, help="Show logs for specific date (YYYY-MM-DD).")
@click.option("--last", "-n", default=20, type=int, help="Number of entries to show.")
def history(date: str | None, last: int):
    """View historical usage data from log files."""
    from claude_usage.display import display_history
    from claude_usage.log_writer import read_logs

    entries = read_logs(date=date, last=last)
    display_history(entries)


if __name__ == "__main__":
    cli()
