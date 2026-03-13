"""Save PR comment exports to disk in various formats."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from .models import PRCommentExport

console = Console()


def save_json(export: PRCommentExport, output: Path) -> Path:
    """Save the full export as structured JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    data = export.model_dump(mode="json")
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def save_markdown(export: PRCommentExport, output: Path) -> Path:
    """Save a human-readable Markdown summary alongside the JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    pr = export.pr

    lines.append(f"# PR #{pr.number}: {pr.title}")
    lines.append("")
    lines.append(f"- **Author:** {pr.author}")
    lines.append(f"- **State:** {pr.state}")
    lines.append(f"- **Branch:** `{pr.head_branch}` -> `{pr.base_branch}`")
    lines.append(f"- **URL:** {pr.url}")
    lines.append("")

    # Stats
    s = export.stats
    lines.append("## Stats")
    lines.append("")
    lines.append(f"- Total comments: {s.total_comments}")
    lines.append(f"- Issue comments: {s.issue_comments}")
    lines.append(f"- Review body comments: {s.review_comments}")
    lines.append(f"- Inline comments: {s.inline_comments}")
    lines.append(f"- Unresolved threads: {s.unresolved_threads}")
    lines.append(f"- Authors: {', '.join(s.unique_authors)}")
    if s.reviews_by_state:
        lines.append(f"- Reviews: {', '.join(f'{k}: {v}' for k, v in s.reviews_by_state.items())}")
    lines.append("")

    # Files with comments
    if s.files_with_comments:
        lines.append("## Files with comments")
        lines.append("")
        for f in s.files_with_comments:
            lines.append(f"- `{f}`")
        lines.append("")

    # Comments grouped by type
    lines.append("## Comments")
    lines.append("")

    for comment in export.comments:
        resolved_tag = ""
        if comment.is_resolved is True:
            resolved_tag = " [RESOLVED]"
        elif comment.is_resolved is False:
            resolved_tag = " [UNRESOLVED]"

        type_label = comment.type.value.upper()
        header = f"### [{type_label}] {comment.author} ({comment.created_at:%Y-%m-%d %H:%M}){resolved_tag}"
        lines.append(header)
        lines.append("")

        if comment.position and comment.position.path:
            loc = f"`{comment.position.path}`"
            if comment.position.line:
                loc += f" L{comment.position.line}"
            lines.append(f"**File:** {loc}")
            lines.append("")

        if comment.in_reply_to_id:
            lines.append(f"*Reply to comment #{comment.in_reply_to_id}*")
            lines.append("")

        lines.append(comment.body)
        lines.append("")
        lines.append("---")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def print_summary(export: PRCommentExport) -> None:
    """Print a summary to the console."""
    s = export.stats
    pr = export.pr

    console.print(f"\n[bold]PR #{pr.number}:[/bold] {pr.title}")
    console.print(f"  [dim]{pr.url}[/dim]")
    console.print()
    console.print(f"  Comments: [bold]{s.total_comments}[/bold] total")
    console.print(f"    Issue: {s.issue_comments} | Review: {s.review_comments} | Inline: {s.inline_comments}")
    console.print(f"  Unresolved threads: [bold red]{s.unresolved_threads}[/bold red]")
    console.print(f"  Authors: {', '.join(s.unique_authors)}")
    if s.files_with_comments:
        console.print(f"  Files: {len(s.files_with_comments)}")
    console.print()
