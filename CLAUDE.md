# Toolbox — Claude Code Guidelines

## Project Overview

This is a monorepo of developer tools, boilerplates, and infrastructure configurations. Tools are Python CLI apps installed via `pip install -e .` from their directory.

## Tool Creation Standards

When creating new tools in `tools/`:

### Structure

```
tools/<tool-name>/
├── pyproject.toml          # setuptools, entry_points for CLI
├── <package_name>/
│   ├── __init__.py
│   ├── cli.py              # Click CLI entry point
│   ├── config.py           # pydantic-settings, env prefix: <TOOL>_
│   ├── models.py           # Pydantic data models
│   └── ...                 # Feature modules
```

### Stack

- **CLI framework**: Click
- **Output**: Rich (tables, panels, colors)
- **Config**: pydantic-settings with `extra="ignore"` (tools run in other repos with their own .env)
- **Models**: Pydantic v2
- **HTTP**: httpx
- **Python**: 3.11+
- **Auth**: OAuth via `~/.claude/.credentials.json` (reuse pattern from claude-usage/auth.py)

### Key Patterns

- **Config singleton**: `settings = Settings()` at module level, import everywhere
- **Lazy imports**: Import heavy modules inside functions in cli.py, not at top level
- **Error handling**: Catch and display with Rich, don't leak tracebacks to users
- **Windows compat**: Use `encoding="utf-8"` and `errors="replace"` for all file I/O. Avoid Unicode chars that fail on cp1252 (use ASCII alternatives: `#` instead of `█`)
- **Exit codes**: Exit 0 for success, 1 for issues found / errors
- **JSON mode**: Always support `--json` flag for structured output (Claude Code integration)

### Claude API Access (OAuth)

Tools that call Claude use the Max subscription via OAuth:
- Token from `~/.claude/.credentials.json` (key: `claudeAiOauth`)
- Bearer auth to `https://api.anthropic.com/v1/messages`
- Headers: `anthropic-version: 2023-06-01`, `anthropic-beta: oauth-2025-04-20`
- Auto-refresh via `https://platform.claude.com/v1/oauth/token`
- Model IDs (OAuth): `claude-sonnet-4-5`, `claude-haiku-4-5-20251001`, `claude-opus-4-6` (use short IDs without date when possible)

### Available Tools

- **claude-usage**: Monitor Claude API usage (check, watch, history, stats)
- **pr-comments**: Fetch GitHub PR comments (fetch, summary)
- **code-review**: AI code review + auto-fix (review, fix, learn, pr, hook)
- **voice-feedback**: Whisper transcription

### Skills (Claude Code Commands)

Global skills in `~/.claude/commands/`:
- `/usage` — Check Claude usage before/during work

## Working in This Repo

- Commit messages: `feat|fix|chore(<scope>): description`
- Don't commit `__pycache__/`, `*.pyc`, `*.db`, `.env`
- Test tools manually after changes: `pip install -e . && <tool-name> --help`
- Use `[skip ci]` in commit messages when pushing to repos with CI you want to bypass
