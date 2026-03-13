"""CLI entry point for pr-comments."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from .formatter import print_summary, save_json, save_markdown
from .github_client import fetch_all

console = Console()


def _parse_pr_ref(pr_ref: str) -> tuple[str, int]:
    """Parse a PR reference into (repo, number).

    Accepts:
      - Full URL: https://github.com/owner/repo/pull/123
      - Shorthand: owner/repo#123
      - Just a number (uses current repo from gh): 123
    """
    # Full URL
    url_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_ref)
    if url_match:
        return url_match.group(1), int(url_match.group(2))

    # owner/repo#123
    short_match = re.match(r"([^/]+/[^#]+)#(\d+)", pr_ref)
    if short_match:
        return short_match.group(1), int(short_match.group(2))

    # Just a number — resolve repo from current git context
    if pr_ref.isdigit():
        try:
            result = subprocess.run(
                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                capture_output=True,
                text=True,
                check=True,
            )
            repo = result.stdout.strip()
            return repo, int(pr_ref)
        except subprocess.CalledProcessError:
            console.print("[red]Could not detect repo. Use owner/repo#number or a full URL.[/red]")
            sys.exit(1)

    console.print(f"[red]Cannot parse PR reference:[/red] {pr_ref}")
    console.print("  Use: URL, owner/repo#123, or just the PR number (in a git repo)")
    sys.exit(1)


@click.group()
def cli() -> None:
    """Download and format GitHub PR comments for systematic processing."""


@cli.command()
@click.argument("pr_ref")
@click.option(
    "-o", "--output",
    type=click.Path(),
    default=None,
    help="Output directory (default: ./pr-comments/<repo>/<number>/)",
)
@click.option(
    "--json-only",
    is_flag=True,
    help="Only save JSON, skip Markdown summary.",
)
@click.option(
    "--unresolved-only",
    is_flag=True,
    help="Only include unresolved inline comment threads.",
)
def fetch(pr_ref: str, output: str | None, json_only: bool, unresolved_only: bool) -> None:
    """Fetch all comments from a GitHub PR.

    PR_REF can be a URL, owner/repo#number, or just a PR number.
    """
    repo, pr_number = _parse_pr_ref(pr_ref)

    console.print(f"Fetching comments for [bold]{repo}#{pr_number}[/bold] ...")

    try:
        export = fetch_all(repo, pr_number)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]GitHub API error:[/red] {e.stderr or e}")
        sys.exit(1)

    if unresolved_only:
        # Keep only unresolved inline threads and their replies
        unresolved_root_ids = {
            c.id
            for c in export.comments
            if c.type.value == "inline"
            and c.in_reply_to_id is None
            and c.is_resolved is not True
        }
        export.comments = [
            c
            for c in export.comments
            if c.type.value != "inline"
            or c.id in unresolved_root_ids
            or c.in_reply_to_id in unresolved_root_ids
        ]

    # Determine output path
    if output:
        out_dir = Path(output)
    else:
        safe_repo = repo.replace("/", "_")
        out_dir = Path("pr-comments") / safe_repo / str(pr_number)

    json_path = save_json(export, out_dir / "comments.json")
    console.print(f"  Saved: [green]{json_path}[/green]")

    if not json_only:
        md_path = save_markdown(export, out_dir / "comments.md")
        console.print(f"  Saved: [green]{md_path}[/green]")

    print_summary(export)


@cli.command()
@click.argument("json_path", type=click.Path(exists=True))
def summary(json_path: str) -> None:
    """Print a summary of a previously exported comments.json file."""
    import json as json_mod

    from .models import PRCommentExport

    data = json_mod.loads(Path(json_path).read_text(encoding="utf-8"))
    export = PRCommentExport.model_validate(data)
    print_summary(export)
