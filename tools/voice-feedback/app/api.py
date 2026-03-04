"""FastAPI server for the voice-feedback analysis pipeline.

Endpoints
---------
POST /api/v1/transcribe     Upload audio -> transcript
POST /api/v1/analyze        Upload audio -> full analysis
POST /api/v1/analyze-text   Submit text  -> analysis
GET  /api/v1/sessions       List past sessions
GET  /api/v1/sessions/{id}  Get a specific session
GET  /health                Health check
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.analyzer import analyze
from app.config import settings
from app.models import AnalysisResult, Session, TranscriptResult
from app.posthog_sync import create_annotation, sync_session
from app.transcriber import SUPPORTED_FORMATS, transcribe

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Feedback Analysis",
    description="Transcribe customer conversations, extract actionable insights, and sync to PostHog.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


@app.on_event("startup")
def _startup() -> None:
    settings.ensure_dirs()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "status": "ok",
        "whisper_model": settings.whisper_model,
        "analysis_provider": settings.analysis_provider,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_upload(upload: UploadFile) -> Path:
    """Persist an uploaded file to UPLOAD_DIR and return the path."""
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    dest = settings.upload_dir / upload.filename
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest


def _save_session(session: Session) -> Path:
    """Write a session to OUTPUT_DIR as JSON."""
    dest = settings.output_dir / session.to_filename()
    dest.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    return dest


def _load_sessions() -> list[Session]:
    """Read all session files from OUTPUT_DIR."""
    sessions: list[Session] = []
    for path in sorted(settings.output_dir.glob("session_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append(Session.model_validate(data))
        except Exception:
            logger.warning("Skipping invalid session file: %s", path.name)
    return sessions


def _load_session_by_id(session_id: str) -> Session:
    """Find and load a session by its id."""
    for path in settings.output_dir.glob("session_*.json"):
        if session_id in path.name:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Session.model_validate(data)
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


# ---------------------------------------------------------------------------
# POST /api/v1/transcribe
# ---------------------------------------------------------------------------


@app.post("/api/v1/transcribe", response_model=TranscriptResult)
def api_transcribe(file: UploadFile = File(...)):
    """Upload an audio file and receive the transcript."""
    path = _save_upload(file)
    try:
        result = transcribe(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# POST /api/v1/analyze
# ---------------------------------------------------------------------------


@app.post("/api/v1/analyze", response_model=Session)
def api_analyze(file: UploadFile = File(...)):
    """Upload an audio file, transcribe it, analyse the transcript, and return the full session."""
    path = _save_upload(file)

    # Transcribe
    try:
        transcript = transcribe(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")

    # Analyse
    try:
        analysis = analyze(transcript)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    # Build session
    session = Session(
        timestamp=datetime.utcnow(),
        audio_file=file.filename,
        transcript=transcript,
        analysis=analysis,
    )
    _save_session(session)

    # PostHog sync (best-effort)
    try:
        sync_session(session)
        if analysis.urgency.value in ("high", "critical"):
            create_annotation(session.id, analysis.summary)
    except Exception as exc:
        logger.warning("PostHog sync failed (non-fatal): %s", exc)

    return session


# ---------------------------------------------------------------------------
# POST /api/v1/analyze-text
# ---------------------------------------------------------------------------


class TextInput(BaseModel):
    text: str
    language: str = "unknown"


@app.post("/api/v1/analyze-text", response_model=Session)
def api_analyze_text(body: TextInput):
    """Submit a text transcript for analysis (no audio upload needed)."""
    transcript = TranscriptResult(
        text=body.text,
        segments=[],
        language=body.language,
        duration=0.0,
    )

    try:
        analysis = analyze(transcript)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    session = Session(
        timestamp=datetime.utcnow(),
        audio_file=None,
        transcript=transcript,
        analysis=analysis,
    )
    _save_session(session)

    # PostHog sync (best-effort)
    try:
        sync_session(session)
    except Exception as exc:
        logger.warning("PostHog sync failed (non-fatal): %s", exc)

    return session


# ---------------------------------------------------------------------------
# GET /api/v1/sessions
# ---------------------------------------------------------------------------


@app.get("/api/v1/sessions")
def api_list_sessions(limit: int = 50, offset: int = 0):
    """List past analysis sessions (newest first)."""
    sessions = _load_sessions()
    sliced = sessions[offset : offset + limit]
    return {
        "total": len(sessions),
        "limit": limit,
        "offset": offset,
        "sessions": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat(),
                "audio_file": s.audio_file,
                "sentiment": s.analysis.sentiment.value if s.analysis else None,
                "urgency": s.analysis.urgency.value if s.analysis else None,
                "item_count": len(s.analysis.items) if s.analysis else 0,
            }
            for s in sliced
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/sessions/{id}
# ---------------------------------------------------------------------------


@app.get("/api/v1/sessions/{session_id}", response_model=Session)
def api_get_session(session_id: str):
    """Get the full details of a specific session."""
    return _load_session_by_id(session_id)
