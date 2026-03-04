"""Audio transcription service using Whisper.

Tries ``faster-whisper`` first (CTranslate2 backend, significantly faster on
CPU and GPU).  Falls back to the original ``openai-whisper`` package when
faster-whisper is not installed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from app.config import settings
from app.models import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)

# Supported audio formats — Whisper / ffmpeg handles all of these.
SUPPORTED_FORMATS: set[str] = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".wma"}


def _is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# faster-whisper backend
# ---------------------------------------------------------------------------


def _transcribe_faster_whisper(
    audio_path: Path,
    model_size: str,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> TranscriptResult:
    """Transcribe using the faster-whisper library (CTranslate2)."""
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    logger.info("Using faster-whisper with model '%s'", model_size)
    model = WhisperModel(model_size, device="auto", compute_type="auto")

    segments_iter, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
    )

    segments: list[TranscriptSegment] = []
    full_text_parts: list[str] = []

    for seg in segments_iter:
        segments.append(
            TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                confidence=seg.avg_log_prob,  # log-prob; higher is better
            )
        )
        full_text_parts.append(seg.text.strip())

        if progress_cb and info.duration:
            progress_cb(min(seg.end / info.duration, 1.0))

    return TranscriptResult(
        text=" ".join(full_text_parts),
        segments=segments,
        language=info.language or "unknown",
        duration=info.duration,
    )


# ---------------------------------------------------------------------------
# openai-whisper backend (fallback)
# ---------------------------------------------------------------------------


def _transcribe_openai_whisper(
    audio_path: Path,
    model_size: str,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> TranscriptResult:
    """Transcribe using the original openai-whisper library."""
    import whisper  # type: ignore[import-untyped]

    logger.info("Using openai-whisper with model '%s'", model_size)
    model = whisper.load_model(model_size)
    result = model.transcribe(str(audio_path), verbose=False)

    segments: list[TranscriptSegment] = []
    for seg in result.get("segments", []):
        segments.append(
            TranscriptSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("avg_logprob", 0.0),
            )
        )

    duration = segments[-1].end if segments else 0.0

    if progress_cb:
        progress_cb(1.0)

    return TranscriptResult(
        text=result["text"].strip(),
        segments=segments,
        language=result.get("language", "unknown"),
        duration=duration,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe(
    audio_path: str | Path,
    model_size: str | None = None,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> TranscriptResult:
    """Transcribe an audio file and return structured results.

    Parameters
    ----------
    audio_path:
        Path to the audio file (mp3, wav, m4a, ogg, webm, flac, wma).
    model_size:
        Whisper model size override.  Falls back to ``settings.whisper_model``.
    progress_cb:
        Optional callback ``(progress: float) -> None`` with values 0.0 .. 1.0.

    Returns
    -------
    TranscriptResult
        The full transcript with timed segments and detected language.

    Raises
    ------
    FileNotFoundError
        If the audio file does not exist.
    ValueError
        If the file format is not supported.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if not _is_supported(path):
        raise ValueError(
            f"Unsupported format '{path.suffix}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    size = model_size or settings.whisper_model

    # Try faster-whisper first, then fall back to openai-whisper.
    try:
        return _transcribe_faster_whisper(path, size, progress_cb)
    except ImportError:
        logger.info("faster-whisper not available, falling back to openai-whisper")
    try:
        return _transcribe_openai_whisper(path, size, progress_cb)
    except ImportError:
        raise ImportError(
            "No Whisper backend found. Install either 'faster-whisper' or 'openai-whisper'."
        )
