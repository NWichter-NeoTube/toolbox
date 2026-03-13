"""Data models for code review."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NITPICK = "nitpick"


class Issue(BaseModel):
    file: str
    line: int
    severity: Severity
    category: str  # bug, security, performance, style, logic
    message: str
    suggestion: str | None = None


class FileContext(BaseModel):
    path: str
    diff: str
    context: str  # surrounding lines
    full_content: str | None = None


class ReviewResult(BaseModel):
    target: str  # commit SHA or PR URL
    files_reviewed: int
    issues: list[Issue]
    summary: str
    model_used: str
    tokens_used: int = 0


class Fix(BaseModel):
    file: str
    original: str
    replacement: str
    issue: Issue


class FixResult(BaseModel):
    fixes_applied: list[Fix] = []
    fixes_failed: list[str] = []
    commit_sha: str | None = None
