# pr-comments

Alle Kommentare eines GitHub Pull Requests herunterladen und als strukturiertes JSON speichern — ideal für die systematische Abarbeitung durch andere Tools (z.B. Claude Code, Skripte).

## Features

- **Alle Kommentar-Typen:** Issue-Kommentare, Review-Bodys und Inline-Kommentare auf Code-Zeilen
- **Resolved-Status:** Erkennt über GraphQL, welche Threads aufgelöst sind
- **Flexible Eingabe:** URL, `owner/repo#123` oder einfach die PR-Nummer
- **Zwei Ausgabeformate:** Strukturiertes JSON (maschinenlesbar) + Markdown (menschenlesbar)
- **Filter:** `--unresolved-only` für nur offene Threads

## Voraussetzungen

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) installiert und eingeloggt (`gh auth login`)

## Installation

```bash
cd tools/pr-comments
pip install -e .
```

## Verwendung

```bash
# Per URL
pr-comments fetch https://github.com/owner/repo/pull/123

# Per Kurzform
pr-comments fetch owner/repo#123

# Nur PR-Nummer (erkennt Repo automatisch wenn im Git-Verzeichnis)
pr-comments fetch 123

# Nur JSON, kein Markdown
pr-comments fetch owner/repo#123 --json-only

# Nur ungelöste Threads
pr-comments fetch owner/repo#123 --unresolved-only

# Eigenes Ausgabeverzeichnis
pr-comments fetch owner/repo#123 -o ./output

# Zusammenfassung einer vorhandenen Export-Datei
pr-comments summary ./pr-comments/owner_repo/123/comments.json
```

## Ausgabeformat

### JSON (`comments.json`)

```json
{
  "exported_at": "2026-03-13T10:00:00+01:00",
  "pr": {
    "number": 123,
    "title": "Add feature X",
    "author": "user",
    "state": "open",
    "base_branch": "main",
    "head_branch": "feature-x",
    "url": "https://github.com/owner/repo/pull/123",
    "created_at": "...",
    "updated_at": "..."
  },
  "reviews": [...],
  "comments": [
    {
      "id": 456,
      "type": "inline",
      "author": "reviewer",
      "body": "This should use a constant.",
      "created_at": "...",
      "updated_at": "...",
      "url": "...",
      "position": {
        "path": "src/main.py",
        "line": 42,
        "diff_hunk": "..."
      },
      "review_id": 789,
      "in_reply_to_id": null,
      "is_resolved": false
    }
  ],
  "stats": {
    "total_comments": 15,
    "issue_comments": 3,
    "review_comments": 2,
    "inline_comments": 10,
    "unique_authors": ["user1", "user2"],
    "reviews_by_state": {"APPROVED": 1, "CHANGES_REQUESTED": 1},
    "unresolved_threads": 4,
    "files_with_comments": ["src/main.py", "src/utils.py"]
  }
}
```

### Kommentar-Typen

| Type     | Beschreibung                                         |
|----------|------------------------------------------------------|
| `issue`  | Allgemeine Kommentare in der PR-Konversation         |
| `review` | Review-Body (Text beim Approve/Request Changes)      |
| `inline` | Zeilenkommentare direkt am Code (mit Datei + Zeile)  |

### Threads

Inline-Kommentare bilden Threads. Der erste Kommentar hat `in_reply_to_id: null`, Antworten verweisen auf die `id` des Eltern-Kommentars. `is_resolved` zeigt, ob der Thread aufgelöst wurde.

## Integration mit anderen Tools

Das JSON ist so strukturiert, dass es einfach von Skripten oder AI-Tools weiterverarbeitet werden kann:

```python
import json
data = json.loads(Path("comments.json").read_text())

# Alle ungelösten Inline-Kommentare
unresolved = [
    c for c in data["comments"]
    if c["type"] == "inline"
    and c["in_reply_to_id"] is None
    and c.get("is_resolved") is not True
]

for c in unresolved:
    print(f"{c['position']['path']}:{c['position']['line']} - {c['author']}: {c['body'][:80]}")
```
