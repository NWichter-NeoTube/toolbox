"""Pydantic models for the voice-feedback analysis pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackType(str, Enum):
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    PAIN_POINT = "pain_point"
    PRAISE = "praise"
    CHURN_RISK = "churn_risk"
    GENERAL = "general"


class AnalysisProvider(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"


# ---------------------------------------------------------------------------
# Transcription models
# ---------------------------------------------------------------------------


class TranscriptSegment(BaseModel):
    """A single segment of a transcript with timing information."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"
    )


class TranscriptResult(BaseModel):
    """Result of a full audio transcription."""

    text: str = Field(..., description="Full transcribed text")
    segments: list[TranscriptSegment] = Field(
        default_factory=list, description="Timed segments"
    )
    language: str = Field(default="unknown", description="Detected language code (e.g. 'de', 'en')")
    duration: float = Field(default=0.0, ge=0.0, description="Audio duration in seconds")


# ---------------------------------------------------------------------------
# Analysis models
# ---------------------------------------------------------------------------


class FeedbackItem(BaseModel):
    """A single extracted feedback item from a transcript."""

    type: FeedbackType = Field(..., description="Category of this feedback item")
    text: str = Field(..., description="Summary of the feedback")
    quote: str = Field(default="", description="Direct quote from the transcript")
    urgency: Urgency = Field(default=Urgency.MEDIUM, description="Urgency level")
    tags: list[str] = Field(default_factory=list, description="Free-form tags")


class AnalysisResult(BaseModel):
    """Complete analysis of a transcript."""

    items: list[FeedbackItem] = Field(
        default_factory=list, description="Extracted feedback items"
    )
    sentiment: Sentiment = Field(
        default=Sentiment.NEUTRAL, description="Overall sentiment"
    )
    topics: list[str] = Field(default_factory=list, description="Key topics mentioned")
    summary: str = Field(default="", description="Brief summary of the conversation")
    suggestions: list[str] = Field(
        default_factory=list, description="Prioritized improvement suggestions"
    )
    urgency: Urgency = Field(
        default=Urgency.MEDIUM, description="Overall urgency level"
    )
    provider: AnalysisProvider = Field(
        default=AnalysisProvider.LOCAL, description="Which analysis backend was used"
    )


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------


class Session(BaseModel):
    """A complete feedback analysis session combining transcript and analysis."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    audio_file: Optional[str] = Field(
        default=None, description="Original audio file name"
    )
    transcript: Optional[TranscriptResult] = None
    analysis: Optional[AnalysisResult] = None

    def to_filename(self) -> str:
        """Return a file-system-safe filename for persisting this session."""
        ts = self.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"session_{ts}_{self.id}.json"
