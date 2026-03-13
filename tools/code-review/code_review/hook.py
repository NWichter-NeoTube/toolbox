"""Git hook management."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from code_review.git_ops import get_repo_root

console = Console()

HOOK_MARKER = "# code-review-hook"
HOOK_SCRIPT = f"""{HOOK_MARKER}
code-review --json 2>/dev/null || true
{HOOK_MARKER}-end
"""


def install(repo_root: Path | None = None) -> None:
    """Install code-review as a post-commit hook."""
    root = repo_root or get_repo_root()
    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "post-commit"

    if hook_file.exists():
        content = hook_file.read_text(encoding="utf-8")
        if HOOK_MARKER in content:
            console.print("[yellow]Hook already installed.[/yellow]")
            return
        content = content.rstrip() + "\n\n" + HOOK_SCRIPT
    else:
        content = "#!/bin/sh\n\n" + HOOK_SCRIPT

    hook_file.write_text(content, encoding="utf-8")
    hook_file.chmod(0o755)
    console.print(f"[green]Post-commit hook installed at {hook_file}[/green]")


def uninstall(repo_root: Path | None = None) -> None:
    """Remove code-review from post-commit hook."""
    root = repo_root or get_repo_root()
    hook_file = root / ".git" / "hooks" / "post-commit"

    if not hook_file.exists():
        console.print("[yellow]No post-commit hook found.[/yellow]")
        return

    content = hook_file.read_text(encoding="utf-8")
    if HOOK_MARKER not in content:
        console.print("[yellow]code-review hook not found in post-commit.[/yellow]")
        return

    # Remove our section
    lines = content.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        if HOOK_MARKER in line and "-end" not in line:
            skip = True
            continue
        if f"{HOOK_MARKER}-end" in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    hook_file.write_text("\n".join(new_lines), encoding="utf-8")
    console.print("[green]Hook removed.[/green]")
