"""Prompt templates for review and fix."""

from __future__ import annotations

import os

from code_review.models import FileContext, Issue

REVIEW_SYSTEM = """You are a senior code reviewer. Analyze the provided diffs and surrounding context.

Find bugs, security issues, performance problems, and logic errors. Focus on real issues, not style nitpicks.

Respond with ONLY a valid JSON array of issues. No markdown, no explanation, just JSON.

Each issue object has these fields:
- "file": string (file path)
- "line": integer (line number)
- "severity": "error" | "warning" | "suggestion"
- "category": "bug" | "security" | "performance" | "logic" | "style"
- "message": string (clear description of the issue)
- "suggestion": string or null (brief fix suggestion)

If there are no issues, return an empty array: []

Focus on:
- Bugs that will cause runtime errors
- Security vulnerabilities (injection, auth bypass, data leaks)
- Logic errors that produce wrong results
- Performance issues (N+1 queries, blocking calls, memory leaks)
- Missing error handling for likely failure paths

Do NOT flag:
- Missing docstrings or comments
- Minor style preferences
- Type annotation completeness
- Import ordering"""


FIX_SYSTEM = """You are a senior developer fixing a code review issue. You will receive a file's content and an issue to fix.

Respond with ONLY a valid JSON object. No markdown, no explanation, just JSON.

The JSON object has these fields:
- "original": string (the exact substring in the file to replace — must match exactly)
- "replacement": string (the new code to replace it with)

Rules:
- The "original" must be a verbatim substring of the file content
- Include enough context in "original" to be unique (a few surrounding lines)
- Keep the fix minimal — only change what's needed
- Preserve indentation and style"""


LEARN_SYSTEM = """You are analyzing PR review comments to extract reusable review rules.

From the provided PR comments, extract concrete, actionable review rules that should be checked in future code reviews.

Respond with ONLY a valid JSON array. Each object has:
- "rule": string (the review rule, concise and actionable)
- "category": "bug" | "security" | "performance" | "logic" | "style"

Only extract rules that are:
- General enough to apply across projects
- Specific enough to be actionable
- About code quality, not project-specific conventions

Return at most 15 rules. Skip duplicates and trivial suggestions."""


def build_review_prompt(files: list[FileContext]) -> tuple[str, list[dict]]:
    """Build the review prompt with learned knowledge."""
    from code_review.knowledge import get_patterns_for_prompt, get_rules_for_prompt

    parts = []
    for f in files:
        parts.append(
            f"## {f.path}\n\n### Diff:\n```\n{f.diff}\n```\n\n### Context:\n```\n{f.context}\n```"
        )

    user_msg = "Review the following changes:\n\n" + "\n\n---\n\n".join(parts)

    # Inject learned knowledge
    system = REVIEW_SYSTEM
    rules = get_rules_for_prompt()
    if rules:
        system += "\n\n" + rules

    file_exts = list({os.path.splitext(f.path)[1] for f in files if f.path})
    patterns = get_patterns_for_prompt(file_exts)
    if patterns:
        system += "\n\n" + patterns

    return system, [{"role": "user", "content": user_msg}]


def build_fix_prompt(issue: Issue, file_content: str) -> tuple[str, list[dict]]:
    """Build the fix prompt."""
    user_msg = (
        f"File: {issue.file}\n\n"
        f"```\n{file_content}\n```\n\n"
        f"Issue at line {issue.line} ({issue.severity.value}, {issue.category}):\n"
        f"{issue.message}\n"
    )
    if issue.suggestion:
        user_msg += f"\nSuggested approach: {issue.suggestion}"

    return FIX_SYSTEM, [{"role": "user", "content": user_msg}]


def build_learn_prompt(comments_text: str) -> tuple[str, list[dict]]:
    """Build the prompt for learning from PR comments."""
    user_msg = (
        "Extract reusable review rules from these PR review comments:\n\n"
        f"{comments_text}"
    )
    return LEARN_SYSTEM, [{"role": "user", "content": user_msg}]
