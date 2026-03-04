"""Tests for the local (rule-based) analyzer.

Covers German and English sample transcripts with various feedback types.
"""

from __future__ import annotations

import pytest

from app.analyzer import analyze
from app.models import (
    AnalysisProvider,
    FeedbackType,
    Sentiment,
    TranscriptResult,
    Urgency,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript(text: str, language: str = "en") -> TranscriptResult:
    return TranscriptResult(text=text, segments=[], language=language, duration=60.0)


def _item_types(result) -> set[str]:
    return {item.type.value for item in result.items}


# ---------------------------------------------------------------------------
# German transcripts
# ---------------------------------------------------------------------------


class TestLocalAnalyzerGerman:
    """Test local analyser with German input."""

    def test_feature_request_de(self):
        text = "Es waere schoen wenn man die Daten als CSV exportieren koennte. Das fehlt uns echt."
        # Use the umlaut variant the regex expects
        text_umlaut = "Es wäre schön wenn man die Daten als CSV exportieren könnte. Das fehlt uns echt."
        result = analyze(_make_transcript(text_umlaut, language="de"), provider="local")

        assert result.provider == AnalysisProvider.LOCAL
        assert any(i.type == FeedbackType.FEATURE_REQUEST for i in result.items)

    def test_bug_report_de(self):
        text = "Die Suchfunktion funktioniert nicht mehr seit dem letzten Update. Es kommt immer ein Fehler."
        result = analyze(_make_transcript(text, language="de"), provider="local")

        assert any(i.type == FeedbackType.BUG_REPORT for i in result.items)

    def test_pain_point_de(self):
        text = "Ich verstehe nicht wie ich die Rechnung herunterladen kann. Das ist total unklar."
        result = analyze(_make_transcript(text, language="de"), provider="local")

        assert any(i.type == FeedbackType.PAIN_POINT for i in result.items)

    def test_praise_de(self):
        text = "Das neue Dashboard ist super, wirklich toll gemacht. Gefällt mir sehr gut."
        result = analyze(_make_transcript(text, language="de"), provider="local")

        assert any(i.type == FeedbackType.PRAISE for i in result.items)
        assert result.sentiment in (Sentiment.POSITIVE, Sentiment.NEUTRAL)

    def test_churn_risk_de(self):
        text = "Wir überlegen zu kündigen und zu einer Alternative zu wechseln."
        result = analyze(_make_transcript(text, language="de"), provider="local")

        assert any(i.type == FeedbackType.CHURN_RISK for i in result.items)
        assert result.urgency in (Urgency.HIGH, Urgency.CRITICAL)

    def test_mixed_german_feedback(self):
        text = (
            "Also das Onboarding ist super, das hat toll funktioniert. "
            "Aber die Export-Funktion funktioniert nicht. "
            "Es wäre schön wenn man auch PDF exportieren könnte. "
            "Wir überlegen gerade ob wir zu einer Alternative wechseln."
        )
        result = analyze(_make_transcript(text, language="de"), provider="local")

        types = _item_types(result)
        assert "praise" in types
        assert "bug_report" in types
        assert "feature_request" in types
        assert "churn_risk" in types
        assert result.urgency == Urgency.CRITICAL  # churn risk present


# ---------------------------------------------------------------------------
# English transcripts
# ---------------------------------------------------------------------------


class TestLocalAnalyzerEnglish:
    """Test local analyser with English input."""

    def test_feature_request_en(self):
        text = "I wish we could schedule reports. It would be nice to have automated exports."
        result = analyze(_make_transcript(text, language="en"), provider="local")

        assert any(i.type == FeedbackType.FEATURE_REQUEST for i in result.items)

    def test_bug_report_en(self):
        text = "The save button is broken. Every time I click it, the page crashes."
        result = analyze(_make_transcript(text, language="en"), provider="local")

        assert any(i.type == FeedbackType.BUG_REPORT for i in result.items)

    def test_pain_point_en(self):
        text = "This is really confusing. How do I find the billing page? It's not intuitive at all."
        result = analyze(_make_transcript(text, language="en"), provider="local")

        assert any(i.type == FeedbackType.PAIN_POINT for i in result.items)

    def test_praise_en(self):
        text = "The new onboarding flow is amazing. I love it. Works really well."
        result = analyze(_make_transcript(text, language="en"), provider="local")

        assert any(i.type == FeedbackType.PRAISE for i in result.items)

    def test_churn_risk_en(self):
        text = "We are looking at competitors. Honestly, we might cancel and switch to something else."
        result = analyze(_make_transcript(text, language="en"), provider="local")

        assert any(i.type == FeedbackType.CHURN_RISK for i in result.items)
        assert result.urgency in (Urgency.HIGH, Urgency.CRITICAL)

    def test_mixed_english_feedback(self):
        text = (
            "Overall the product is great, the team loves it. "
            "But the export feature doesn't work properly, it throws an error. "
            "I wish there was a way to bulk-edit items. "
            "How do I find the admin settings? It's really confusing. "
            "If this isn't fixed soon we might stop using the platform."
        )
        result = analyze(_make_transcript(text, language="en"), provider="local")

        types = _item_types(result)
        assert "praise" in types
        assert "bug_report" in types
        assert "feature_request" in types
        assert "pain_point" in types
        assert "churn_risk" in types


# ---------------------------------------------------------------------------
# Sentiment detection
# ---------------------------------------------------------------------------


class TestSentiment:
    """Test overall sentiment classification."""

    def test_positive_sentiment(self):
        text = "This is amazing, really great work. I love the dashboard, it's fantastic and perfect."
        result = analyze(_make_transcript(text), provider="local")
        assert result.sentiment == Sentiment.POSITIVE

    def test_negative_sentiment(self):
        text = "This is terrible, really bad. I'm disappointed and frustrated. The worst experience."
        result = analyze(_make_transcript(text), provider="local")
        assert result.sentiment == Sentiment.NEGATIVE

    def test_neutral_sentiment(self):
        text = "The product has some features. We use it for our daily work."
        result = analyze(_make_transcript(text), provider="local")
        assert result.sentiment == Sentiment.NEUTRAL


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_transcript(self):
        result = analyze(_make_transcript(""), provider="local")
        assert result.items == []
        assert result.urgency == Urgency.LOW

    def test_very_short_transcript(self):
        result = analyze(_make_transcript("Hi."), provider="local")
        assert result.items == []

    def test_no_feedback_content(self):
        text = "We talked about the weather today. It was raining outside."
        result = analyze(_make_transcript(text), provider="local")
        assert len(result.items) == 0
        assert result.urgency == Urgency.LOW

    def test_topics_extracted(self):
        text = (
            "The dashboard loading time is really slow. "
            "The dashboard needs better filtering. "
            "Dashboard performance should be improved."
        )
        result = analyze(_make_transcript(text), provider="local")
        assert "dashboard" in result.topics

    def test_suggestions_generated_for_bugs(self):
        text = "The login page doesn't work and the save button is broken."
        result = analyze(_make_transcript(text), provider="local")
        assert any("bug" in s.lower() or "fix" in s.lower() for s in result.suggestions)

    def test_provider_field(self):
        result = analyze(_make_transcript("Hello world"), provider="local")
        assert result.provider == AnalysisProvider.LOCAL
