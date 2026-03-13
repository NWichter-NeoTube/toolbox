"""Fetch PR data from GitHub using the gh CLI."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime

from .models import (
    Comment,
    CommentType,
    ExportStats,
    InlinePosition,
    PRCommentExport,
    PRInfo,
    Review,
    ReviewState,
)


def _gh(args: list[str]) -> dict | list:
    """Run a gh api command and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _gh_paginated(endpoint: str) -> list:
    """Fetch all pages from a paginated GitHub API endpoint."""
    result = subprocess.run(
        ["gh", "api", endpoint, "--paginate"],
        capture_output=True,
        text=True,
        check=True,
    )
    # gh --paginate concatenates JSON arrays, which may result in multiple
    # arrays. We handle both single-array and multi-array output.
    text = result.stdout.strip()
    if not text:
        return []

    # gh --paginate for arrays outputs them concatenated: [..][..]
    # We need to handle this by splitting on "][" boundaries
    items = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        # Skip whitespace
        while pos < len(text) and text[pos] in " \t\n\r":
            pos += 1
        if pos >= len(text):
            break
        obj, end = decoder.raw_decode(text, pos)
        if isinstance(obj, list):
            items.extend(obj)
        else:
            items.append(obj)
        pos = end

    return items


def _parse_dt(s: str | None) -> datetime:
    if not s:
        return datetime.min
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_pr_info(repo: str, pr_number: int) -> PRInfo:
    """Fetch basic PR metadata."""
    data = _gh([f"/repos/{repo}/pulls/{pr_number}"])
    return PRInfo(
        number=data["number"],
        title=data["title"],
        author=data["user"]["login"],
        state=data["state"],
        base_branch=data["base"]["ref"],
        head_branch=data["head"]["ref"],
        url=data["html_url"],
        created_at=_parse_dt(data["created_at"]),
        updated_at=_parse_dt(data["updated_at"]),
    )


def fetch_issue_comments(repo: str, pr_number: int) -> list[Comment]:
    """Fetch general conversation comments on the PR."""
    data = _gh_paginated(f"/repos/{repo}/issues/{pr_number}/comments")
    return [
        Comment(
            id=c["id"],
            type=CommentType.ISSUE,
            author=c["user"]["login"],
            body=c["body"] or "",
            created_at=_parse_dt(c["created_at"]),
            updated_at=_parse_dt(c["updated_at"]),
            url=c["html_url"],
        )
        for c in data
    ]


def fetch_reviews(repo: str, pr_number: int) -> list[Review]:
    """Fetch all reviews on the PR."""
    data = _gh_paginated(f"/repos/{repo}/pulls/{pr_number}/reviews")
    return [
        Review(
            id=r["id"],
            author=r["user"]["login"],
            state=ReviewState(r["state"]),
            body=r["body"] or "",
            submitted_at=_parse_dt(r["submitted_at"]),
            url=r["html_url"],
        )
        for r in data
    ]


def fetch_review_comments(repo: str, pr_number: int) -> list[Comment]:
    """Fetch all inline/review comments on the PR."""
    data = _gh_paginated(f"/repos/{repo}/pulls/{pr_number}/comments")
    comments = []
    for c in data:
        position = InlinePosition(
            path=c.get("path", ""),
            start_line=c.get("start_line"),
            line=c.get("line") or c.get("original_line"),
            side=c.get("side"),
            diff_hunk=c.get("diff_hunk"),
        )
        comments.append(
            Comment(
                id=c["id"],
                type=CommentType.INLINE,
                author=c["user"]["login"],
                body=c["body"] or "",
                created_at=_parse_dt(c["created_at"]),
                updated_at=_parse_dt(c["updated_at"]),
                url=c["html_url"],
                position=position,
                review_id=c.get("pull_request_review_id"),
                in_reply_to_id=c.get("in_reply_to_id"),
            )
        )
    return comments


def fetch_all(repo: str, pr_number: int) -> PRCommentExport:
    """Fetch all PR data and assemble the complete export."""
    pr_info = fetch_pr_info(repo, pr_number)
    issue_comments = fetch_issue_comments(repo, pr_number)
    reviews = fetch_reviews(repo, pr_number)
    review_comments = fetch_review_comments(repo, pr_number)

    # Mark resolved threads (inline comments that have a resolved marker)
    # GitHub doesn't directly expose "resolved" in the REST API,
    # but we can use the GraphQL API for that
    _enrich_resolved_status(repo, pr_number, review_comments)

    # Build review-body comments (reviews with non-empty body)
    review_body_comments = [
        Comment(
            id=r.id,
            type=CommentType.REVIEW,
            author=r.author,
            body=r.body,
            created_at=r.submitted_at,
            updated_at=r.submitted_at,
            url=r.url,
            review_id=r.id,
        )
        for r in reviews
        if r.body.strip()
    ]

    all_comments = sorted(
        issue_comments + review_body_comments + review_comments,
        key=lambda c: c.created_at,
    )

    # Compute stats
    unique_authors = sorted({c.author for c in all_comments})
    reviews_by_state: dict[str, int] = {}
    for r in reviews:
        reviews_by_state[r.state.value] = reviews_by_state.get(r.state.value, 0) + 1

    files_with_comments = sorted({
        c.position.path for c in all_comments if c.position and c.position.path
    })

    # Count unresolved threads (top-level inline comments that are not resolved)
    top_level_inline = [
        c for c in review_comments if c.in_reply_to_id is None
    ]
    unresolved = sum(1 for c in top_level_inline if c.is_resolved is False or c.is_resolved is None)

    stats = ExportStats(
        total_comments=len(all_comments),
        issue_comments=len(issue_comments),
        review_comments=len(review_body_comments),
        inline_comments=len(review_comments),
        unique_authors=unique_authors,
        reviews_by_state=reviews_by_state,
        unresolved_threads=unresolved,
        files_with_comments=files_with_comments,
    )

    return PRCommentExport(
        exported_at=datetime.now().astimezone(),
        pr=pr_info,
        reviews=reviews,
        comments=all_comments,
        stats=stats,
    )


def _enrich_resolved_status(repo: str, pr_number: int, comments: list[Comment]) -> None:
    """Use GraphQL to fetch thread resolved status and enrich inline comments."""
    owner, name = repo.split("/")
    query = """
    query($owner: String!, $name: String!, $pr: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              isResolved
              comments(first: 1) {
                nodes { databaseId }
              }
            }
          }
        }
      }
    }
    """

    resolved_map: dict[int, bool] = {}
    cursor = None

    while True:
        variables = {"owner": owner, "name": name, "pr": pr_number}
        if cursor:
            variables["cursor"] = cursor

        try:
            result = subprocess.run(
                [
                    "gh", "api", "graphql",
                    "-f", f"query={query}",
                    "-f", f"variables={json.dumps(variables)}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return  # Silently skip if GraphQL fails

        threads_data = data.get("data", {}).get("repository", {}).get("pullRequest", {}).get("reviewThreads", {})
        for node in threads_data.get("nodes", []):
            first_comments = node.get("comments", {}).get("nodes", [])
            if first_comments:
                db_id = first_comments[0].get("databaseId")
                if db_id:
                    resolved_map[db_id] = node["isResolved"]

        page_info = threads_data.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
        else:
            break

    # Apply resolved status to comments
    for comment in comments:
        if comment.id in resolved_map:
            comment.is_resolved = resolved_map[comment.id]
        elif comment.in_reply_to_id and comment.in_reply_to_id in resolved_map:
            comment.is_resolved = resolved_map[comment.in_reply_to_id]
