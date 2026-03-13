"""Review orchestration: diff -> prompt -> Claude -> issues."""

from __future__ import annotations

import json

from rich.console import Console

from code_review.api_client import call_claude
from code_review.config import settings
from code_review.git_ops import (
    get_changed_files_from_diff,
    get_changed_lines_from_diff,
    get_diff,
    get_file_context,
    get_last_commit_sha,
    get_pr_base_branch,
    get_pr_diff,
)
from code_review.models import FileContext, Issue, ReviewResult, Severity
from code_review.prompts import build_review_prompt

console = Console(stderr=True)

# Approximate token limit per API call (leave room for response)
MAX_PROMPT_CHARS = 400_000  # ~100K tokens


def _build_file_contexts(diff: str) -> list[FileContext]:
    files = get_changed_files_from_diff(diff)
    contexts = []

    # Split diff into per-file chunks
    file_diffs: dict[str, str] = {}
    current_file = None
    current_lines: list[str] = []
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_file:
                file_diffs[current_file] = "\n".join(current_lines)
            current_file = line.split(" b/")[-1] if " b/" in line else None
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_file:
        file_diffs[current_file] = "\n".join(current_lines)

    for filepath in files:
        file_diff = file_diffs.get(filepath, "")
        changed_lines = get_changed_lines_from_diff(diff, filepath)
        try:
            context = get_file_context(filepath, changed_lines, settings.context_lines)
        except Exception:
            context = ""
        contexts.append(FileContext(path=filepath, diff=file_diff, context=context))

    return contexts


def _parse_issues(response: str) -> list[Issue]:
    """Parse Claude's JSON response into Issue objects."""
    text = response.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(raw, list):
        return []

    issues = []
    for item in raw:
        try:
            sev = item.get("severity", "suggestion")
            if sev not in {s.value for s in Severity}:
                sev = "suggestion"
            issues.append(
                Issue(
                    file=item["file"],
                    line=item.get("line", 0),
                    severity=Severity(sev),
                    category=item.get("category", "logic"),
                    message=item["message"],
                    suggestion=item.get("suggestion"),
                )
            )
        except (KeyError, ValueError):
            continue

    return issues


def _review_file_contexts(contexts: list[FileContext], target: str, model: str) -> ReviewResult:
    """Send file contexts in batches to Claude and collect issues."""
    all_issues: list[Issue] = []
    total_tokens = 0

    # Batch files to fit within token limits
    batches: list[list[FileContext]] = []
    current_batch: list[FileContext] = []
    current_size = 0

    for ctx in contexts:
        size = len(ctx.diff) + len(ctx.context)
        if current_size + size > MAX_PROMPT_CHARS and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(ctx)
        current_size += size

    if current_batch:
        batches.append(current_batch)

    for i, batch in enumerate(batches):
        if len(batches) > 1:
            console.print(f"  Reviewing batch {i + 1}/{len(batches)} ({len(batch)} files)...")

        system, messages = build_review_prompt(batch)
        response, tokens = call_claude(
            messages=messages,
            model=model,
            system=system,
            max_tokens=settings.max_tokens_review,
        )
        total_tokens += tokens
        all_issues.extend(_parse_issues(response))

    # Auto-learn patterns from found issues
    try:
        from code_review.knowledge import record_pattern
        import os

        for issue in all_issues:
            ext = os.path.splitext(issue.file)[1] if issue.file else "*"
            record_pattern(issue.category, issue.message, ext)
    except Exception:
        pass  # Don't fail review if pattern recording fails

    # Build summary
    errors = sum(1 for i in all_issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in all_issues if i.severity == Severity.WARNING)
    suggestions = sum(1 for i in all_issues if i.severity == Severity.SUGGESTION)
    summary = f"{len(all_issues)} issues: {errors} errors, {warnings} warnings, {suggestions} suggestions"

    return ReviewResult(
        target=target,
        files_reviewed=len(contexts),
        issues=all_issues,
        summary=summary,
        model_used=model,
        tokens_used=total_tokens,
    )


def review_commit(commit_range: str = "HEAD~1..HEAD") -> ReviewResult:
    """Review the last commit."""
    sha = get_last_commit_sha()
    console.print(f"  Reviewing commit [bold]{sha}[/bold]...")

    diff = get_diff(commit_range)
    if not diff.strip():
        return ReviewResult(
            target=sha, files_reviewed=0, issues=[], summary="No changes.", model_used="", tokens_used=0
        )

    contexts = _build_file_contexts(diff)
    console.print(f"  {len(contexts)} files changed")

    return _review_file_contexts(contexts, sha, settings.review_model)


def review_pr(pr_url: str) -> ReviewResult:
    """Review an entire PR."""
    console.print(f"  Fetching PR info...")
    base, head, _ = get_pr_base_branch(pr_url)
    console.print(f"  Reviewing [bold]{head}[/bold] → [bold]{base}[/bold]...")

    diff = get_pr_diff(f"origin/{base}", head)
    if not diff.strip():
        return ReviewResult(
            target=pr_url, files_reviewed=0, issues=[], summary="No changes.", model_used="", tokens_used=0
        )

    contexts = _build_file_contexts(diff)
    console.print(f"  {len(contexts)} files changed")

    return _review_file_contexts(contexts, pr_url, settings.review_model)


def learn_from_pr_comments(comments_json_path: str) -> int:
    """Extract reusable rules from PR comments and add to knowledge base."""
    import json as json_mod
    from pathlib import Path

    from code_review.knowledge import add_rule, record_pattern
    from code_review.prompts import build_learn_prompt

    data = json_mod.loads(Path(comments_json_path).read_text(encoding="utf-8"))

    # Collect inline comment bodies (skip replies)
    comment_texts = []
    for c in data.get("comments", []):
        if c.get("type") != "inline":
            continue
        if c.get("in_reply_to_id"):
            continue
        body = c.get("body", "")
        pos = c.get("position") or {}
        path = pos.get("path", "")
        comment_texts.append(f"[{path}] {body[:500]}")

    if not comment_texts:
        return 0

    # Send to Claude for rule extraction
    text = "\n\n---\n\n".join(comment_texts[:50])  # Cap at 50 comments
    system, messages = build_learn_prompt(text)
    response, _ = call_claude(
        messages=messages,
        model=settings.review_model,
        system=system,
        max_tokens=2048,
    )

    # Parse rules
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]

    try:
        rules = json_mod.loads(text.strip())
    except json_mod.JSONDecodeError:
        return 0

    count = 0
    source = data.get("pr", {}).get("url", comments_json_path)
    for r in rules:
        if isinstance(r, dict) and "rule" in r:
            add_rule(r["rule"], source=source, category=r.get("category", "general"))
            count += 1

    # Also record patterns from the actual issues found
    for c in data.get("comments", []):
        if c.get("type") != "inline" or c.get("in_reply_to_id"):
            continue
        pos = c.get("position") or {}
        path = pos.get("path", "")
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else "*"
        body = c.get("body", "")[:200]
        if body:
            record_pattern(category="pr-feedback", message=body, file_ext=ext)

    return count
