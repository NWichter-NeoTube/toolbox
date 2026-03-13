"""Git operations: diff extraction, file reading, fix application, commits."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def run_git(*args: str, cwd: str | Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def get_repo_root() -> Path:
    return Path(run_git("rev-parse", "--show-toplevel").strip())


def get_last_commit_sha() -> str:
    return run_git("rev-parse", "--short", "HEAD").strip()


def get_diff(commit_range: str = "HEAD~1..HEAD") -> str:
    return run_git("diff", commit_range, "--unified=3")


def get_pr_diff(base: str, head: str = "HEAD") -> str:
    return run_git("diff", f"{base}...{head}", "--unified=3")


def get_changed_files_from_diff(diff: str) -> list[str]:
    """Extract file paths from unified diff."""
    files = []
    for match in re.finditer(r"^diff --git a/.+ b/(.+)$", diff, re.MULTILINE):
        files.append(match.group(1))
    return files


def get_changed_lines_from_diff(diff: str, filepath: str) -> list[int]:
    """Extract changed line numbers for a specific file from a diff."""
    lines = []
    in_file = False
    current_line = 0

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            in_file = line.endswith(f"b/{filepath}")
            continue
        if not in_file:
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            current_line = int(hunk.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(current_line)
            current_line += 1
        elif line.startswith("-"):
            pass  # deleted line, don't increment
        else:
            current_line += 1

    return lines


def get_file_context(filepath: str, changed_lines: list[int], context: int = 50) -> str:
    """Read file and extract regions around changed lines."""
    repo = get_repo_root()
    full_path = repo / filepath
    if not full_path.exists():
        return ""

    all_lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not changed_lines:
        return "\n".join(all_lines[:context * 2])

    # Build set of line numbers to include
    include = set()
    for ln in changed_lines:
        for i in range(max(1, ln - context), min(len(all_lines) + 1, ln + context + 1)):
            include.add(i)

    result = []
    prev = 0
    for i in sorted(include):
        if i > prev + 1 and prev > 0:
            result.append(f"... (lines {prev + 1}-{i - 1} omitted) ...")
        result.append(f"{i:4d} | {all_lines[i - 1]}")
        prev = i

    return "\n".join(result)


def get_file_content(filepath: str) -> str:
    repo = get_repo_root()
    return (repo / filepath).read_text(encoding="utf-8", errors="replace")


def apply_fix(filepath: str, original: str, replacement: str) -> bool:
    """Apply a string replacement to a file. Returns True on success."""
    repo = get_repo_root()
    full_path = repo / filepath
    content = full_path.read_text(encoding="utf-8", errors="replace")
    if original not in content:
        return False
    content = content.replace(original, replacement, 1)
    full_path.write_text(content, encoding="utf-8")
    return True


def create_commit(message: str, files: list[str]) -> str:
    """Stage files and commit. Returns the new commit SHA."""
    for f in files:
        run_git("add", f)
    run_git("commit", "-m", message)
    return get_last_commit_sha()


def get_pr_base_branch(pr_url: str) -> tuple[str, str, str]:
    """Use gh to get (base_branch, head_branch, repo) from a PR URL."""
    result = subprocess.run(
        [
            "gh", "pr", "view", pr_url,
            "--json", "baseRefName,headRefName,headRepository",
            "-q", ".baseRefName + \" \" + .headRefName",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh pr view failed: {result.stderr.strip()}")
    parts = result.stdout.strip().split()
    return parts[0], parts[1], pr_url
