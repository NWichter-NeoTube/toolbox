"""Pydantic models for PR comment data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class CommentType(str, Enum):
    """Type of PR comment."""

    ISSUE = "issue"  # General PR conversation comments
    REVIEW = "review"  # Review-level comments (approve/request changes/comment)
    INLINE = "inline"  # Line-level review comments on specific code


class ReviewState(str, Enum):
    """State of a review."""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"
    PENDING = "PENDING"


class InlinePosition(BaseModel):
    """Position information for inline comments."""

    path: str
    start_line: int | None = None
    line: int | None = None
    side: str | None = None  # LEFT or RIGHT
    diff_hunk: str | None = None


class Comment(BaseModel):
    """A single comment from a PR."""

    id: int
    type: CommentType
    author: str
    body: str
    created_at: datetime
    updated_at: datetime
    url: str

    # For inline comments
    position: InlinePosition | None = None

    # For review comments: which review they belong to
    review_id: int | None = None

    # Thread info for inline comments
    in_reply_to_id: int | None = None
    is_resolved: bool | None = None


class Review(BaseModel):
    """A PR review (container for inline comments)."""

    id: int
    author: str
    state: ReviewState
    body: str
    submitted_at: datetime
    url: str


class PRInfo(BaseModel):
    """Basic PR metadata."""

    number: int
    title: str
    author: str
    state: str
    base_branch: str
    head_branch: str
    url: str
    created_at: datetime
    updated_at: datetime


class PRCommentExport(BaseModel):
    """Complete export of all PR comments."""

    exported_at: datetime
    pr: PRInfo
    reviews: list[Review]
    comments: list[Comment]
    stats: ExportStats


class ExportStats(BaseModel):
    """Summary statistics for the export."""

    total_comments: int
    issue_comments: int
    review_comments: int
    inline_comments: int
    unique_authors: list[str]
    reviews_by_state: dict[str, int]
    unresolved_threads: int
    files_with_comments: list[str]
