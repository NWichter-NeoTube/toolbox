"""CLI entry point for code-review."""

from __future__ import annotations

import sys

import click
from rich.console import Console

console = Console(stderr=True)

OPUS_MODEL = "claude-opus-4-6"


def _apply_opus(ctx: click.Context) -> None:
    """Override both review and fix models to Opus if --opus was passed."""
    if ctx.obj.get("opus"):
        from code_review.config import settings

        settings.review_model = OPUS_MODEL
        settings.fix_model = OPUS_MODEL


@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Output JSON (for piping / Claude Code)")
@click.option("--opus", is_flag=True, help="Use Opus 4.6 instead of Sonnet (higher quality, uses Opus budget)")
@click.option("--range", "commit_range", default="HEAD~1..HEAD", help="Commit range to review")
@click.pass_context
def cli(ctx: click.Context, json_output: bool, opus: bool, commit_range: str) -> None:
    """AI-powered code review using Claude."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["opus"] = opus
    ctx.obj["range"] = commit_range

    if ctx.invoked_subcommand is None:
        ctx.invoke(review)


@cli.command()
@click.pass_context
def review(ctx: click.Context) -> None:
    """Review the last commit's diff."""
    _apply_opus(ctx)
    from code_review.display import display_json, display_review
    from code_review.reviewer import review_commit

    result = review_commit(ctx.obj.get("range", "HEAD~1..HEAD"))

    if ctx.obj.get("json"):
        display_json(result)
    else:
        display_review(result)

    if result.issues:
        sys.exit(1)


@cli.command()
@click.pass_context
def fix(ctx: click.Context) -> None:
    """Review last commit + auto-fix issues + new commit."""
    _apply_opus(ctx)
    from code_review.display import display_fix_result, display_review
    from code_review.fixer import fix_issues
    from code_review.reviewer import review_commit

    result = review_commit(ctx.obj.get("range", "HEAD~1..HEAD"))
    display_review(result)

    if not result.issues:
        return

    console.print("\n  Generating fixes...")
    fix_result = fix_issues(result.issues)
    display_fix_result(fix_result)


@cli.group(invoke_without_command=True)
@click.argument("url", required=False)
@click.pass_context
def pr(ctx: click.Context, url: str | None) -> None:
    """Review a GitHub PR."""
    ctx.ensure_object(dict)

    if ctx.invoked_subcommand is None:
        if not url:
            click.echo("Usage: code-review pr <url>")
            sys.exit(1)
        ctx.obj["pr_url"] = url
        ctx.invoke(pr_review)


@pr.command("review")
@click.pass_context
def pr_review(ctx: click.Context) -> None:
    """Review an entire PR's diff."""
    _apply_opus(ctx)
    from code_review.display import display_json, display_review
    from code_review.reviewer import review_pr

    url = ctx.obj.get("pr_url", "")
    result = review_pr(url)

    if ctx.obj.get("json"):
        display_json(result)
    else:
        display_review(result)


@pr.command("fix")
@click.argument("url")
@click.pass_context
def pr_fix(ctx: click.Context, url: str) -> None:
    """Review PR + auto-fix all issues."""
    _apply_opus(ctx)
    from code_review.display import display_fix_result, display_review
    from code_review.fixer import fix_issues
    from code_review.reviewer import review_pr

    result = review_pr(url)
    display_review(result)

    if not result.issues:
        return

    console.print("\n  Generating fixes...")
    fix_result = fix_issues(result.issues)
    display_fix_result(fix_result)


@cli.command()
@click.argument("comments_json", type=click.Path(exists=True))
def learn(comments_json: str) -> None:
    """Learn review rules from PR comments JSON file.

    Use with pr-comments output: code-review learn comments.json
    """
    from code_review.reviewer import learn_from_pr_comments

    console.print(f"  Learning from [bold]{comments_json}[/bold]...")
    count = learn_from_pr_comments(comments_json)
    console.print(f"  [green]Learned {count} new rules[/green]")


@cli.command()
def rules() -> None:
    """Show all learned review rules."""
    from rich.table import Table

    from code_review.knowledge import get_rules

    all_rules = get_rules()
    if not all_rules:
        console.print("  No rules learned yet. Use 'code-review learn <comments.json>' to add some.")
        return

    table = Table(title="Learned Review Rules")
    table.add_column("#", width=4)
    table.add_column("Category", width=12)
    table.add_column("Rule", min_width=50)
    table.add_column("Seen", width=5)
    table.add_column("Source", max_width=30)

    for i, r in enumerate(all_rules):
        table.add_row(
            str(i),
            r.get("category", ""),
            r["rule"],
            str(r.get("seen_count", 1)),
            r.get("source", "")[:30],
        )

    console.print(table)


@cli.group()
def hook() -> None:
    """Git hook management."""


@hook.command()
def install() -> None:
    """Install as post-commit git hook in current repo."""
    from code_review.hook import install as do_install

    do_install()


@hook.command()
def uninstall() -> None:
    """Remove post-commit git hook."""
    from code_review.hook import uninstall as do_uninstall

    do_uninstall()
