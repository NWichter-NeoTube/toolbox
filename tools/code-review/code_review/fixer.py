"""Fix orchestration: issue -> Claude -> apply replacement -> commit."""

from __future__ import annotations

import json
from collections import defaultdict

from rich.console import Console

from code_review.api_client import call_claude
from code_review.config import settings
from code_review.git_ops import apply_fix, create_commit, get_file_content
from code_review.models import Fix, FixResult, Issue
from code_review.prompts import build_fix_prompt

console = Console(stderr=True)


def _parse_fix(response: str) -> tuple[str, str] | None:
    """Parse Claude's fix response into (original, replacement)."""
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    original = data.get("original")
    replacement = data.get("replacement")
    if not original or replacement is None:
        return None

    return original, replacement


def fix_issues(issues: list[Issue]) -> FixResult:
    """Generate and apply fixes for all issues."""
    result = FixResult()

    # Group by file to process together
    by_file: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        by_file[issue.file].append(issue)

    changed_files: list[str] = []

    for filepath, file_issues in by_file.items():
        console.print(f"  Fixing [bold]{filepath}[/bold] ({len(file_issues)} issues)...")

        try:
            content = get_file_content(filepath)
        except Exception as e:
            for issue in file_issues:
                result.fixes_failed.append(f"{filepath}:{issue.line} - Cannot read file: {e}")
            continue

        file_changed = False
        for issue in file_issues:
            system, messages = build_fix_prompt(issue, content)
            try:
                response, _tokens = call_claude(
                    messages=messages,
                    model=settings.fix_model,
                    system=system,
                    max_tokens=settings.max_tokens_fix,
                )
            except Exception as e:
                result.fixes_failed.append(f"{filepath}:{issue.line} - API error: {e}")
                continue

            parsed = _parse_fix(response)
            if not parsed:
                result.fixes_failed.append(f"{filepath}:{issue.line} - Could not parse fix response")
                continue

            original, replacement = parsed
            fix = Fix(file=filepath, original=original, replacement=replacement, issue=issue)

            if apply_fix(filepath, original, replacement):
                result.fixes_applied.append(fix)
                file_changed = True
                # Re-read file for next fix in same file
                content = get_file_content(filepath)
            else:
                result.fixes_failed.append(
                    f"{filepath}:{issue.line} - Original string not found in file"
                )

        if file_changed:
            changed_files.append(filepath)

    if changed_files and settings.auto_commit:
        try:
            sha = create_commit(
                f"fix: address {len(result.fixes_applied)} code review issues",
                changed_files,
            )
            result.commit_sha = sha
        except Exception as e:
            console.print(f"  [yellow]Warning: Could not commit: {e}[/yellow]")

    return result
