"""Transcript analysis service.

Two modes:
  1. **local** -- Rule-based keyword extraction.  Works offline, no API keys
     required.  Supports German and English keywords.
  2. **openai** -- GPT-4 structured analysis via the OpenAI API.  Higher
     quality but requires an API key and sends data externally.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from app.config import settings
from app.models import (
    AnalysisProvider,
    AnalysisResult,
    FeedbackItem,
    FeedbackType,
    Sentiment,
    TranscriptResult,
    Urgency,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bilingual keyword patterns (German + English)
# ---------------------------------------------------------------------------

KEYWORD_PATTERNS: dict[FeedbackType, list[str]] = {
    FeedbackType.FEATURE_REQUEST: [
        # German
        r"wäre schön wenn",
        r"wäre toll wenn",
        r"es fehlt",
        r"man bräuchte",
        r"man könnte",
        r"wünsche mir",
        r"sollte.*können",
        r"fehlt.*funktion",
        r"hätte gerne",
        r"brauchen wir",
        r"wäre hilfreich",
        # English
        r"i wish",
        r"would be nice",
        r"it would help if",
        r"we need",
        r"can you add",
        r"would love",
        r"feature request",
        r"it('s| is) missing",
        r"there('s| is) no way to",
        r"would be great if",
        r"should be able to",
        r"we really need",
    ],
    FeedbackType.BUG_REPORT: [
        # German
        r"funktioniert nicht",
        r"geht nicht",
        r"fehler",
        r"kaputt",
        r"stürzt ab",
        r"absturz",
        r"hängt sich auf",
        r"lädt nicht",
        r"fehlermeldung",
        r"bug",
        r"defekt",
        # English
        r"doesn('t| not) work",
        r"broken",
        r"error",
        r"crash(es|ed|ing)?",
        r"bug",
        r"not loading",
        r"freezes",
        r"stuck",
        r"fails",
        r"not responding",
        r"throws an? (error|exception)",
    ],
    FeedbackType.PAIN_POINT: [
        # German
        r"verstehe nicht",
        r"unklar",
        r"verwirrend",
        r"kompliziert",
        r"schwierig",
        r"umständlich",
        r"dauert zu lange",
        r"nervig",
        r"frustrierend",
        r"wo (ist|finde ich)",
        r"wie (geht|mache ich)",
        # English
        r"confusing",
        r"how do i",
        r"where is",
        r"don('t| not) understand",
        r"unclear",
        r"complicated",
        r"takes too long",
        r"annoying",
        r"frustrating",
        r"hard to (find|use|understand)",
        r"not intuitive",
    ],
    FeedbackType.PRAISE: [
        # German
        r"super",
        r"toll",
        r"perfekt",
        r"genial",
        r"klasse",
        r"hervorragend",
        r"wunderbar",
        r"ausgezeichnet",
        r"gefällt mir",
        r"sehr gut",
        r"top",
        r"prima",
        r"fantastisch",
        # English
        r"great",
        r"love it",
        r"works well",
        r"amazing",
        r"awesome",
        r"excellent",
        r"fantastic",
        r"perfect",
        r"impressed",
        r"well done",
        r"really like",
        r"best (feature|tool|thing)",
    ],
    FeedbackType.CHURN_RISK: [
        # German
        r"kündigen",
        r"alternative",
        r"wechseln",
        r"abmelden",
        r"nicht mehr nutzen",
        r"aufhören",
        r"zu teuer",
        r"konkurrenz",
        r"abwandern",
        r"vertrag beenden",
        # English
        r"cancel",
        r"switch(ing)? to",
        r"looking at",
        r"competitor",
        r"unsubscribe",
        r"too expensive",
        r"not worth",
        r"stop using",
        r"moving away",
        r"looking for alternatives",
        r"considering other",
    ],
}

# Sentiment keyword lists
POSITIVE_KEYWORDS: list[str] = [
    "super", "toll", "perfekt", "genial", "klasse", "hervorragend", "prima",
    "great", "love", "amazing", "awesome", "excellent", "fantastic", "perfect",
    "impressed", "happy", "zufrieden", "begeistert", "wunderbar", "freut",
]
NEGATIVE_KEYWORDS: list[str] = [
    "schlecht", "furchtbar", "schrecklich", "enttäuscht", "ärgerlich", "wütend",
    "bad", "terrible", "awful", "disappointed", "angry", "hate", "worst",
    "horrible", "unacceptable", "frustrierend", "frustrating", "nervig",
]


# ---------------------------------------------------------------------------
# Local (rule-based) analyzer
# ---------------------------------------------------------------------------


def _extract_sentence(text: str, match_start: int, match_end: int) -> str:
    """Extract the sentence surrounding a regex match position."""
    # Walk backward to sentence start
    start = match_start
    while start > 0 and text[start - 1] not in ".!?\n":
        start -= 1

    # Walk forward to sentence end
    end = match_end
    while end < len(text) and text[end] not in ".!?\n":
        end += 1

    return text[start:end].strip()


def _analyze_local(transcript: TranscriptResult) -> AnalysisResult:
    """Analyse a transcript using rule-based keyword extraction."""
    text = transcript.text
    text_lower = text.lower()

    items: list[FeedbackItem] = []
    seen_quotes: set[str] = set()

    for feedback_type, patterns in KEYWORD_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text_lower):
                quote = _extract_sentence(text, match.start(), match.end())
                # Deduplicate overlapping quotes
                if quote in seen_quotes:
                    continue
                seen_quotes.add(quote)

                urgency = Urgency.MEDIUM
                if feedback_type == FeedbackType.CHURN_RISK:
                    urgency = Urgency.HIGH
                elif feedback_type == FeedbackType.BUG_REPORT:
                    urgency = Urgency.HIGH
                elif feedback_type == FeedbackType.PRAISE:
                    urgency = Urgency.LOW

                items.append(
                    FeedbackItem(
                        type=feedback_type,
                        text=f"{feedback_type.value}: matched '{pattern}'",
                        quote=quote,
                        urgency=urgency,
                        tags=[feedback_type.value, transcript.language],
                    )
                )

    # --- Overall sentiment ---------------------------------------------------
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    if pos_count > neg_count + 2:
        sentiment = Sentiment.POSITIVE
    elif neg_count > pos_count + 2:
        sentiment = Sentiment.NEGATIVE
    else:
        sentiment = Sentiment.NEUTRAL

    # --- Topics (simple word-frequency extraction) ---------------------------
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "but", "or",
        "and", "not", "no", "so", "if", "it", "its", "this", "that", "my",
        "your", "we", "our", "they", "them", "their", "i", "me", "you", "he",
        "she", "him", "her", "what", "which", "who", "whom", "how", "when",
        "where", "why", "all", "each", "every", "some", "any", "than", "too",
        "very", "just", "also", "then", "now", "here", "there", "up", "out",
        # German stopwords
        "der", "die", "das", "ein", "eine", "und", "oder", "aber", "ist",
        "sind", "war", "hat", "haben", "nicht", "ich", "wir", "sie", "er",
        "es", "du", "ihr", "uns", "den", "dem", "des", "auf", "mit", "von",
        "für", "an", "bei", "nach", "über", "unter", "vor", "zwischen",
        "durch", "gegen", "ohne", "um", "aus", "zu", "noch", "schon", "dann",
        "wenn", "wie", "was", "wer", "wo", "man", "auch", "nur", "mal",
        "ja", "nein", "so", "da",
    }
    words = re.findall(r"\b[a-zäöüß]{4,}\b", text_lower)
    freq: dict[str, int] = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    topics = sorted(freq, key=freq.get, reverse=True)[:10]  # type: ignore[arg-type]

    # --- Overall urgency -----------------------------------------------------
    type_counts = {ft: 0 for ft in FeedbackType}
    for item in items:
        type_counts[item.type] += 1

    if type_counts[FeedbackType.CHURN_RISK] > 0:
        overall_urgency = Urgency.CRITICAL
    elif type_counts[FeedbackType.BUG_REPORT] >= 3:
        overall_urgency = Urgency.HIGH
    elif type_counts[FeedbackType.BUG_REPORT] >= 1 or type_counts[FeedbackType.PAIN_POINT] >= 2:
        overall_urgency = Urgency.MEDIUM
    else:
        overall_urgency = Urgency.LOW

    # --- Summary / suggestions -----------------------------------------------
    summary_parts: list[str] = []
    if type_counts[FeedbackType.FEATURE_REQUEST]:
        summary_parts.append(
            f"{type_counts[FeedbackType.FEATURE_REQUEST]} feature request(s)"
        )
    if type_counts[FeedbackType.BUG_REPORT]:
        summary_parts.append(f"{type_counts[FeedbackType.BUG_REPORT]} bug report(s)")
    if type_counts[FeedbackType.PAIN_POINT]:
        summary_parts.append(f"{type_counts[FeedbackType.PAIN_POINT]} pain point(s)")
    if type_counts[FeedbackType.PRAISE]:
        summary_parts.append(f"{type_counts[FeedbackType.PRAISE]} positive mention(s)")
    if type_counts[FeedbackType.CHURN_RISK]:
        summary_parts.append(
            f"{type_counts[FeedbackType.CHURN_RISK]} churn risk signal(s)"
        )

    summary = (
        f"Transcript analysis ({transcript.language}): "
        + ", ".join(summary_parts)
        if summary_parts
        else "No notable feedback items detected."
    )

    suggestions: list[str] = []
    if type_counts[FeedbackType.CHURN_RISK]:
        suggestions.append("[CRITICAL] Address churn risk signals immediately — schedule follow-up.")
    if type_counts[FeedbackType.BUG_REPORT]:
        suggestions.append("[HIGH] Investigate and fix reported bugs.")
    if type_counts[FeedbackType.PAIN_POINT]:
        suggestions.append("[MEDIUM] Improve UX for areas causing confusion.")
    if type_counts[FeedbackType.FEATURE_REQUEST]:
        suggestions.append("[MEDIUM] Evaluate feature requests for product roadmap.")
    if type_counts[FeedbackType.PRAISE]:
        suggestions.append("[LOW] Document and reinforce praised areas.")

    return AnalysisResult(
        items=items,
        sentiment=sentiment,
        topics=topics,
        summary=summary,
        suggestions=suggestions,
        urgency=overall_urgency,
        provider=AnalysisProvider.LOCAL,
    )


# ---------------------------------------------------------------------------
# OpenAI (GPT-4) analyzer
# ---------------------------------------------------------------------------

_OPENAI_SYSTEM_PROMPT = """\
You are a product feedback analyst. You receive a transcript of a customer \
conversation and extract structured, actionable insights.

Respond ONLY with valid JSON matching this schema:
{
  "items": [
    {
      "type": "feature_request|bug_report|pain_point|praise|churn_risk|general",
      "text": "short summary",
      "quote": "direct quote from transcript",
      "urgency": "low|medium|high|critical",
      "tags": ["tag1", "tag2"]
    }
  ],
  "sentiment": "positive|neutral|negative",
  "topics": ["topic1", "topic2"],
  "summary": "2-3 sentence summary",
  "suggestions": ["prioritized suggestion 1", "suggestion 2"],
  "urgency": "low|medium|high|critical"
}

Rules:
- Extract ALL feature requests, bug reports, pain points, praise, and churn risk signals.
- Use direct quotes from the transcript for the "quote" field.
- Tags should include the product area (e.g., "onboarding", "billing", "dashboard").
- Suggestions should be prioritized by urgency.
- Support both German and English transcripts.
"""


def _analyze_openai(transcript: TranscriptResult) -> AnalysisResult:
    """Analyse a transcript using the OpenAI API (GPT-4)."""
    from openai import OpenAI

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required when analysis_provider='openai'. "
            "Set it in your environment or .env file."
        )

    client = OpenAI(api_key=settings.openai_api_key)

    user_message = (
        f"Language detected: {transcript.language}\n"
        f"Duration: {transcript.duration:.0f}s\n\n"
        f"Transcript:\n{transcript.text}"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _OPENAI_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    items = [
        FeedbackItem(
            type=FeedbackType(item.get("type", "general")),
            text=item.get("text", ""),
            quote=item.get("quote", ""),
            urgency=Urgency(item.get("urgency", "medium")),
            tags=item.get("tags", []),
        )
        for item in data.get("items", [])
    ]

    return AnalysisResult(
        items=items,
        sentiment=Sentiment(data.get("sentiment", "neutral")),
        topics=data.get("topics", []),
        summary=data.get("summary", ""),
        suggestions=data.get("suggestions", []),
        urgency=Urgency(data.get("urgency", "medium")),
        provider=AnalysisProvider.OPENAI,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(
    transcript: TranscriptResult,
    provider: Optional[str] = None,
) -> AnalysisResult:
    """Analyse a transcript and return structured feedback items.

    Parameters
    ----------
    transcript:
        The transcription result to analyse.
    provider:
        Override for the analysis provider ('local' or 'openai').
        Falls back to ``settings.analysis_provider``.

    Returns
    -------
    AnalysisResult
        Extracted items, sentiment, topics, summary, and suggestions.
    """
    chosen = provider or settings.analysis_provider

    if chosen == AnalysisProvider.OPENAI:
        logger.info("Running OpenAI analysis (model: %s)", settings.openai_model)
        return _analyze_openai(transcript)

    logger.info("Running local rule-based analysis")
    return _analyze_local(transcript)
