"""Global knowledge base — learns from PR comments across all projects.

Stores two types of knowledge:
- rules: Recurring patterns the reviewer should check for (from PR feedback)
- patterns: Common issues seen across projects (auto-extracted from reviews)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from code_review.config import settings


def _load_json(path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path, data: list[dict]) -> None:
    settings.ensure_dirs()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Rules ---

def get_rules() -> list[dict]:
    """Get all learned rules."""
    return _load_json(settings.rules_path)


def add_rule(rule: str, source: str, category: str = "general") -> None:
    """Add a new review rule."""
    rules = get_rules()
    # Deduplicate by checking similarity
    for existing in rules:
        if existing["rule"].lower() == rule.lower():
            existing["seen_count"] = existing.get("seen_count", 1) + 1
            _save_json(settings.rules_path, rules)
            return

    rules.append({
        "rule": rule,
        "category": category,
        "source": source,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "seen_count": 1,
    })
    _save_json(settings.rules_path, rules)


def remove_rule(index: int) -> bool:
    """Remove a rule by index."""
    rules = get_rules()
    if 0 <= index < len(rules):
        rules.pop(index)
        _save_json(settings.rules_path, rules)
        return True
    return False


# --- Patterns (auto-learned from reviews) ---

def get_patterns() -> list[dict]:
    """Get common issue patterns."""
    return _load_json(settings.patterns_path)


def record_pattern(category: str, message: str, file_ext: str) -> None:
    """Record an issue pattern for future reviews."""
    patterns = get_patterns()

    for p in patterns:
        if p["category"] == category and p["file_ext"] == file_ext:
            if _similar(p["message"], message):
                p["count"] = p.get("count", 1) + 1
                p["last_seen"] = datetime.now(timezone.utc).isoformat()
                _save_json(settings.patterns_path, patterns)
                return

    patterns.append({
        "category": category,
        "message": message,
        "file_ext": file_ext,
        "count": 1,
        "last_seen": datetime.now(timezone.utc).isoformat(),
    })
    _save_json(settings.patterns_path, patterns)


def _similar(a: str, b: str) -> bool:
    """Simple similarity check — same first 50 chars."""
    return a[:50].lower() == b[:50].lower()


# --- Format for prompts ---

def get_rules_for_prompt() -> str:
    """Format rules as context for the review prompt."""
    rules = get_rules()
    if not rules:
        return ""

    # Sort by seen_count (most important first), take top 20
    rules = sorted(rules, key=lambda r: r.get("seen_count", 1), reverse=True)[:20]

    lines = ["## Additional review rules (learned from past reviews):"]
    for r in rules:
        lines.append(f"- [{r['category']}] {r['rule']}")

    return "\n".join(lines)


def get_patterns_for_prompt(file_exts: list[str]) -> str:
    """Format relevant patterns as context for the review prompt."""
    patterns = get_patterns()
    if not patterns:
        return ""

    # Filter to relevant file types, sort by frequency
    relevant = [p for p in patterns if p["file_ext"] in file_exts or p["file_ext"] == "*"]
    relevant = sorted(relevant, key=lambda p: p.get("count", 1), reverse=True)[:10]

    if not relevant:
        return ""

    lines = ["## Common issues in this type of code (seen before):"]
    for p in relevant:
        lines.append(f"- [{p['category']}] {p['message']} (seen {p['count']}x)")

    return "\n".join(lines)
