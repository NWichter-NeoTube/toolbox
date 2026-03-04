# Voice Feedback Analysis Tool

Transcribe customer conversations with Whisper, extract actionable product insights, and feed structured results into PostHog.

Part of the [self-hosted SaaS toolbox](../../docs/00-overview.md).

---

## What It Does

1. **Transcribe** audio recordings (mp3, wav, m4a, ogg, webm) using OpenAI Whisper.
2. **Analyse** transcripts for feature requests, bug reports, pain points, praise, and churn risk signals.
3. **Sync** structured insights to PostHog as custom events (`customer_feedback_session`, `customer_feedback_item`).

Two analysis modes:

| Mode   | How It Works                          | Pros                            | Cons                       |
|--------|---------------------------------------|---------------------------------|----------------------------|
| local  | Rule-based keyword matching (DE + EN) | No API key, offline, fast       | Lower accuracy             |
| openai | GPT-4 structured JSON analysis        | High accuracy, nuanced insights | Requires API key, external |

---

## Setup

### Option A: pip install (development)

```bash
cd tools/voice-feedback
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Copy and edit environment variables
cp .env.example .env

# Run
voice-feedback --help
```

**Requirement:** `ffmpeg` must be installed and available on PATH (Whisper needs it).

### Option B: Docker

```bash
cd tools/voice-feedback

docker build -t voice-feedback .

docker run -d \
  --name voice-feedback \
  -p 8000:8000 \
  -v ./uploads:/app/uploads \
  -v ./output:/app/output \
  --env-file .env \
  voice-feedback
```

---

## CLI Usage

```bash
# Transcribe an audio file
voice-feedback transcribe recording.mp3
voice-feedback transcribe recording.mp3 --model small --output transcript.json

# Full analysis pipeline (transcribe + analyse + PostHog sync)
voice-feedback analyze call.m4a
voice-feedback analyze call.m4a --provider openai --no-sync

# Analyse an existing text transcript
voice-feedback analyze-text transcript.txt --language de

# Start the API server
voice-feedback serve
voice-feedback serve --port 9000 --reload

# Pretty-print a past session report
voice-feedback report abc123def456
```

---

## API Usage

Start the server:

```bash
voice-feedback serve
# or: uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Path                       | Description                     |
|--------|----------------------------|---------------------------------|
| POST   | `/api/v1/transcribe`       | Upload audio, get transcript    |
| POST   | `/api/v1/analyze`          | Upload audio, get full analysis |
| POST   | `/api/v1/analyze-text`     | Submit text, get analysis       |
| GET    | `/api/v1/sessions`         | List past sessions              |
| GET    | `/api/v1/sessions/{id}`    | Get a specific session          |
| GET    | `/health`                  | Health check                    |

### curl Examples

```bash
# Transcribe only
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@recording.mp3"

# Full analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@call.m4a"

# Analyse text
curl -X POST http://localhost:8000/api/v1/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text": "The dashboard is great but exporting data does not work.", "language": "en"}'

# List sessions
curl http://localhost:8000/api/v1/sessions

# Get session details
curl http://localhost:8000/api/v1/sessions/abc123def456
```

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI).

---

## How Analysis Works

### Local Mode (default)

The local analyser scans the transcript for bilingual keyword patterns:

| Category        | Example Patterns (DE)                | Example Patterns (EN)               |
|-----------------|--------------------------------------|--------------------------------------|
| Feature request | "waere schoen wenn", "es fehlt"      | "I wish", "would be nice"           |
| Bug report      | "funktioniert nicht", "Fehler"       | "doesn't work", "broken", "crash"   |
| Pain point      | "verstehe nicht", "unklar"           | "confusing", "how do I"             |
| Praise          | "super", "toll", "perfekt"           | "great", "love it", "works well"    |
| Churn risk      | "kuendigen", "alternative"           | "cancel", "switch to"               |

Sentiment is determined by counting positive vs. negative keywords. Topics are extracted via word frequency analysis.

### OpenAI Mode

Set `ANALYSIS_PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in your `.env`. The transcript is sent to GPT-4 with a structured JSON prompt that extracts the same categories with higher accuracy and nuance.

---

## PostHog Integration

When `POSTHOG_API_KEY` is configured, each analysis session creates:

- **`customer_feedback_session`** event with overall sentiment, urgency, topics, and item counts.
- **`customer_feedback_item`** events (one per extracted item) with type, quote, urgency, and tags.

High-urgency sessions also create PostHog **annotations** so they appear as markers on your trend graphs.

In PostHog, you can:
- Filter by `item_type` to see all feature requests or bug reports.
- Build dashboards combining quantitative analytics with qualitative feedback.
- Correlate call feedback with user behaviour data.

---

## DSGVO / Datenschutz

- **Consent required:** Customers must explicitly consent to being recorded before the conversation starts.
- **Local storage:** All recordings and transcripts are stored on your own server. No audio data is sent to third parties (unless you enable OpenAI mode, in which case only the text transcript is sent).
- **Auto-delete:** Consider setting up a cron job to delete audio files from `UPLOAD_DIR` after analysis is complete.
- **PII removal:** Transcripts may contain personal data. Consider anonymising transcripts before long-term storage.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check app/ tests/
ruff format app/ tests/
```

---

## Architecture

```
Audio File (mp3/wav/m4a/ogg/webm)
    |
    v
[Whisper Transcription]  (faster-whisper or openai-whisper)
    |
    v
TranscriptResult (text, segments, language, duration)
    |
    v
[Analysis Engine]  (local keyword matching OR OpenAI GPT-4)
    |
    v
AnalysisResult (items, sentiment, topics, summary, suggestions)
    |
    +---> JSON file in OUTPUT_DIR
    |
    +---> PostHog events (customer_feedback_session + customer_feedback_item)
    |
    +---> PostHog annotation (if high urgency)
```
