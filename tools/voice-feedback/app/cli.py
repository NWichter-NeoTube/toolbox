"""Click CLI for the voice-feedback analysis pipeline.

Commands
--------
voice-feedback transcribe <file>        Transcribe an audio file
voice-feedback analyze <file>           Full analysis pipeline
voice-feedback analyze-text <file.txt>  Analyse an existing text transcript
voice-feedback serve                    Start the API server
voice-feedback report <session-id>      Pretty-print a session report
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from app.config import settings

console = Console()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version="0.1.0", prog_name="voice-feedback")
def cli():
    """Voice-based customer feedback analysis tool."""
    settings.ensure_dirs()


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--model", "-m", default=None, help="Whisper model size override.")
@click.option("--output", "-o", default=None, type=click.Path(path_type=Path), help="Write JSON output to file.")
def transcribe(file: Path, model: str | None, output: Path | None):
    """Transcribe an audio file using Whisper."""
    from app.transcriber import transcribe as do_transcribe

    console.print(f"[bold]Transcribing:[/bold] {file.name}")
    console.print(f"[dim]Model: {model or settings.whisper_model}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Transcribing...", total=None)

        def on_progress(pct: float):
            progress.update(task, description=f"Transcribing... {pct:.0%}")

        result = do_transcribe(file, model_size=model, progress_cb=on_progress)

    console.print()
    console.print(f"[green]Language:[/green] {result.language}")
    console.print(f"[green]Duration:[/green] {result.duration:.1f}s")
    console.print()

    # Segments table
    if result.segments:
        table = Table(title="Segments", show_lines=True)
        table.add_column("Start", style="cyan", width=8)
        table.add_column("End", style="cyan", width=8)
        table.add_column("Text")

        for seg in result.segments[:20]:  # Show first 20 segments
            table.add_row(f"{seg.start:.1f}s", f"{seg.end:.1f}s", seg.text)

        if len(result.segments) > 20:
            table.add_row("...", "...", f"({len(result.segments) - 20} more segments)")

        console.print(table)

    # Full text
    console.print()
    console.print(Panel(result.text, title="Full Transcript", border_style="green"))

    if output:
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n[dim]Saved to {output}[/dim]")


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--model", "-m", default=None, help="Whisper model size override.")
@click.option("--provider", "-p", default=None, type=click.Choice(["local", "openai"]))
@click.option("--sync/--no-sync", default=True, help="Sync results to PostHog.")
def analyze(file: Path, model: str | None, provider: str | None, sync: bool):
    """Transcribe and analyse an audio file (full pipeline)."""
    from app.analyzer import analyze as do_analyze
    from app.models import Session
    from app.posthog_sync import create_annotation, sync_session
    from app.transcriber import transcribe as do_transcribe

    # Step 1: Transcribe
    console.print(f"[bold]Step 1:[/bold] Transcribing {file.name} ...")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Transcribing...", total=None)

        def on_progress(pct: float):
            progress.update(task, description=f"Transcribing... {pct:.0%}")

        transcript = do_transcribe(file, model_size=model, progress_cb=on_progress)

    console.print(f"  [green]Language:[/green] {transcript.language}, [green]Duration:[/green] {transcript.duration:.1f}s\n")

    # Step 2: Analyse
    console.print("[bold]Step 2:[/bold] Analysing transcript ...")
    analysis = do_analyze(transcript, provider=provider)

    # Step 3: Build and save session
    session = Session(
        timestamp=datetime.utcnow(),
        audio_file=file.name,
        transcript=transcript,
        analysis=analysis,
    )
    dest = settings.output_dir / session.to_filename()
    dest.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"  [dim]Session saved: {dest}[/dim]\n")

    # Step 4: PostHog sync
    if sync and settings.posthog_api_key:
        console.print("[bold]Step 3:[/bold] Syncing to PostHog ...")
        try:
            sync_session(session)
            if analysis.urgency.value in ("high", "critical"):
                create_annotation(session.id, analysis.summary)
            console.print("  [green]Synced successfully.[/green]\n")
        except Exception as exc:
            console.print(f"  [yellow]Sync failed (non-fatal): {exc}[/yellow]\n")
    elif sync:
        console.print("[dim]PostHog sync skipped (no API key configured).[/dim]\n")

    # Step 5: Print report
    _print_report(session)


# ---------------------------------------------------------------------------
# analyze-text
# ---------------------------------------------------------------------------


@cli.command("analyze-text")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default="unknown", help="Transcript language code (e.g. de, en).")
@click.option("--provider", "-p", default=None, type=click.Choice(["local", "openai"]))
@click.option("--sync/--no-sync", default=True, help="Sync results to PostHog.")
def analyze_text(file: Path, language: str, provider: str | None, sync: bool):
    """Analyse an existing text transcript file."""
    from app.analyzer import analyze as do_analyze
    from app.models import Session, TranscriptResult
    from app.posthog_sync import sync_session

    text = file.read_text(encoding="utf-8").strip()
    if not text:
        console.print("[red]Error: file is empty.[/red]")
        sys.exit(1)

    transcript = TranscriptResult(text=text, segments=[], language=language, duration=0.0)
    console.print(f"[bold]Analysing:[/bold] {file.name} ({len(text)} characters, language={language})\n")

    analysis = do_analyze(transcript, provider=provider)

    session = Session(
        timestamp=datetime.utcnow(),
        audio_file=None,
        transcript=transcript,
        analysis=analysis,
    )
    dest = settings.output_dir / session.to_filename()
    dest.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"[dim]Session saved: {dest}[/dim]\n")

    if sync and settings.posthog_api_key:
        try:
            sync_session(session)
            console.print("[green]Synced to PostHog.[/green]\n")
        except Exception as exc:
            console.print(f"[yellow]PostHog sync failed: {exc}[/yellow]\n")

    _print_report(session)


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--host", default=None, help="Bind host.")
@click.option("--port", default=None, type=int, help="Bind port.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload for development.")
def serve(host: str | None, port: int | None, do_reload: bool):
    """Start the FastAPI server."""
    import uvicorn

    h = host or settings.api_host
    p = port or settings.api_port

    console.print(f"[bold]Starting server at[/bold] http://{h}:{p}")
    console.print(f"[dim]Docs: http://{h}:{p}/docs[/dim]\n")

    uvicorn.run("app.api:app", host=h, port=p, reload=do_reload)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("session_id")
def report(session_id: str):
    """Pretty-print a session report by session ID."""
    from app.models import Session

    # Find session file
    matches = list(settings.output_dir.glob(f"*{session_id}*.json"))
    if not matches:
        console.print(f"[red]Session '{session_id}' not found in {settings.output_dir}[/red]")
        sys.exit(1)

    data = json.loads(matches[0].read_text(encoding="utf-8"))
    session = Session.model_validate(data)
    _print_report(session)


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

_URGENCY_COLORS = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
    "critical": "bold red",
}

_TYPE_ICONS = {
    "feature_request": "FEAT",
    "bug_report": "BUG",
    "pain_point": "PAIN",
    "praise": "GOOD",
    "churn_risk": "CHURN",
    "general": "INFO",
}


def _print_report(session: Session) -> None:
    """Print a rich-formatted report of a session."""
    console.print()
    console.rule(f"[bold]Session Report: {session.id}[/bold]")
    console.print(f"  Timestamp : {session.timestamp.isoformat()}")
    console.print(f"  Audio file: {session.audio_file or 'N/A'}")

    if session.transcript:
        console.print(f"  Language  : {session.transcript.language}")
        console.print(f"  Duration  : {session.transcript.duration:.1f}s")

    if not session.analysis:
        console.print("\n[yellow]No analysis available.[/yellow]")
        return

    a = session.analysis
    urgency_color = _URGENCY_COLORS.get(a.urgency.value, "white")

    console.print(f"  Sentiment : {a.sentiment.value}")
    console.print(f"  Urgency   : [{urgency_color}]{a.urgency.value.upper()}[/{urgency_color}]")
    console.print(f"  Provider  : {a.provider.value}")
    console.print()

    # Summary
    console.print(Panel(a.summary, title="Summary", border_style="blue"))

    # Topics
    if a.topics:
        console.print(f"[bold]Topics:[/bold] {', '.join(a.topics)}\n")

    # Feedback items table
    if a.items:
        table = Table(title="Feedback Items", show_lines=True, expand=True)
        table.add_column("#", width=3)
        table.add_column("Type", width=7)
        table.add_column("Urgency", width=9)
        table.add_column("Quote", ratio=3)
        table.add_column("Tags", width=20)

        for idx, item in enumerate(a.items, 1):
            u_color = _URGENCY_COLORS.get(item.urgency.value, "white")
            table.add_row(
                str(idx),
                _TYPE_ICONS.get(item.type.value, "?"),
                f"[{u_color}]{item.urgency.value}[/{u_color}]",
                item.quote[:120] + ("..." if len(item.quote) > 120 else ""),
                ", ".join(item.tags),
            )
        console.print(table)

    # Suggestions
    if a.suggestions:
        console.print()
        console.print("[bold]Suggestions:[/bold]")
        for s in a.suggestions:
            console.print(f"  {s}")

    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
