"""Rich terminal output for review results."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from code_review.models import FixResult, ReviewResult, Severity

console = Console()

SEVERITY_COLORS = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.SUGGESTION: "cyan",
    Severity.NITPICK: "dim",
}


def display_review(result: ReviewResult) -> None:
    """Display review results as a Rich table."""
    if not result.issues:
        console.print(
            Panel(
                f"[green]No issues found[/green] in {result.files_reviewed} files.",
                title=f"Review: {result.target}",
            )
        )
        return

    table = Table(title=f"Review: {result.target}")
    table.add_column("Sev", width=8)
    table.add_column("File:Line", min_width=25)
    table.add_column("Cat", width=12)
    table.add_column("Issue", min_width=40)

    for issue in sorted(result.issues, key=lambda i: (i.severity.value, i.file, i.line)):
        color = SEVERITY_COLORS.get(issue.severity, "white")
        sev_label = f"[{color}]{issue.severity.value.upper()}[/{color}]"
        location = f"{issue.file}:{issue.line}"
        msg = issue.message
        if issue.suggestion:
            msg += f"\n  [dim]Fix: {issue.suggestion}[/dim]"

        table.add_row(sev_label, location, issue.category, msg)

    console.print(table)
    console.print(f"\n  {result.summary}")
    console.print(f"  Model: {result.model_used} | Tokens: {result.tokens_used}")


def display_fix_result(result: FixResult) -> None:
    """Display fix results."""
    if result.fixes_applied:
        console.print(f"\n  [green]{len(result.fixes_applied)} fixes applied[/green]")
        for fix in result.fixes_applied:
            console.print(f"    [green]+[/green] {fix.file}:{fix.issue.line} — {fix.issue.message[:80]}")

    if result.fixes_failed:
        console.print(f"\n  [yellow]{len(result.fixes_failed)} fixes failed[/yellow]")
        for msg in result.fixes_failed:
            console.print(f"    [yellow]![/yellow] {msg[:100]}")

    if result.commit_sha:
        console.print(f"\n  Committed: [bold]{result.commit_sha}[/bold]")


def display_json(result: ReviewResult) -> None:
    """Output structured JSON to stdout (for Claude Code integration)."""
    data = result.model_dump(mode="json")
    # Print to stdout (not stderr) so it can be piped
    print(json.dumps(data, indent=2))
