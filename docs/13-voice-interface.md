# 13 -- Voice Interface & Kundengespraech-Analyse

How to record customer conversations, transcribe them with Whisper, extract actionable product insights, and feed results into PostHog.

> **Prerequisites:** Your toolbox stack must be running (see [04-deploy-stack.md](04-deploy-stack.md)). PostHog must be configured for your project (see [10-project-workflow.md](10-project-workflow.md)). The voice-feedback tool must be deployed (see Setup below).

---

## 1. Uebersicht

Customer conversations are the richest source of product feedback. Unlike quantitative analytics (which tell you *what* users do), conversations reveal *why* they do it, what frustrates them, what they wish existed, and whether they are about to leave.

The problem: conversations are unstructured. Insights get lost in notes, recordings sit on laptops, and nobody aggregates them.

This tool solves that by automating the pipeline:

```
Record conversation (with consent)
    |
    v
Upload audio file
    |
    v
Whisper transcribes to text
    |
    v
Analyzer extracts structured items:
  - Feature requests
  - Bug reports
  - Pain points
  - Praise
  - Churn risk signals
    |
    v
Results pushed to PostHog as events
    |
    v
Insights appear on dashboards alongside quantitative data
```

**Why this matters:**
- Feature requests from conversations are weighted input for the roadmap -- they come from real users who describe their actual workflow.
- Bug reports from conversations often include context that Sentry alone does not capture (the user's mental model, what they expected to happen).
- Churn risk signals are early warnings. A customer saying "we might switch" is actionable before they actually leave.
- Combining conversation analysis with PostHog analytics and Sentry error data gives you a 360-degree view of product health.

---

## 2. Architecture

```
+------------------+     +---------------------+     +--------------------+
|  Audio Recording |     |  voice-feedback API  |     |      PostHog       |
|  (phone, browser,| --> |  (FastAPI + Whisper) | --> |  (custom events)   |
|   mobile app)    |     |                      |     |                    |
+------------------+     +----------+-----------+     +--------+-----------+
                                    |                          |
                                    v                          v
                            +-------+--------+         +-------+---------+
                            | JSON sessions  |         | Dashboards      |
                            | (local storage)|         | Trends, Funnels |
                            +----------------+         +-----------------+
```

### Components

| Component          | Technology                        | Purpose                                |
|--------------------|-----------------------------------|----------------------------------------|
| Transcription      | faster-whisper or openai-whisper   | Audio to text (local, on your server)  |
| Analysis (local)   | Rule-based keyword extraction      | Extract feedback items offline          |
| Analysis (OpenAI)  | GPT-4 via OpenAI API              | Higher-quality extraction (optional)   |
| API Server         | FastAPI + uvicorn                 | REST API for uploads and results       |
| CLI                | Click + Rich                      | Terminal interface for manual use       |
| Storage            | JSON files on disk                | Session persistence                    |
| PostHog Sync       | posthog Python SDK                | Push events to PostHog                 |

---

## 3. Setup

The voice-feedback tool lives at `tools/voice-feedback/` in the toolbox repository.

### Option A: Docker (recommended for production)

```bash
cd tools/voice-feedback

# Copy and configure environment
cp .env.example .env
# Edit .env: set POSTHOG_API_KEY, POSTHOG_HOST, WHISPER_MODEL

# Build
docker build -t voice-feedback .

# Run
docker run -d \
  --name voice-feedback \
  --network toolbox \
  -p 8000:8000 \
  -v ./uploads:/app/uploads \
  -v ./output:/app/output \
  --env-file .env \
  voice-feedback
```

Joining the `toolbox` Docker network lets the container reach PostHog directly via its internal hostname (`posthog:8000`). In that case set `POSTHOG_HOST=http://posthog:8000` in your `.env`.

### Option B: Standalone (development)

```bash
cd tools/voice-feedback
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# ffmpeg must be installed (Whisper needs it)
# macOS: brew install ffmpeg
# Ubuntu: apt install ffmpeg
# Windows: choco install ffmpeg

cp .env.example .env
voice-feedback serve --reload
```

### Environment Variables

| Variable            | Default                    | Description                              |
|---------------------|----------------------------|------------------------------------------|
| `WHISPER_MODEL`     | `base`                     | Whisper model size (see table below)     |
| `POSTHOG_API_KEY`   | (empty)                    | PostHog project API key                  |
| `POSTHOG_HOST`      | `https://posthog.example.com` | PostHog instance URL                  |
| `ANALYSIS_PROVIDER` | `local`                    | `local` or `openai`                      |
| `OPENAI_API_KEY`    | (empty)                    | Required only for `openai` provider      |
| `UPLOAD_DIR`        | `./uploads`                | Where audio files are stored             |
| `OUTPUT_DIR`        | `./output`                 | Where session JSON files are written     |

---

## 4. Recording

The tool processes audio files. It does not record audio itself. You can record using any method:

### Browser Recording

Use the Web Audio API to record in the browser and upload via the REST API:

```javascript
// Minimal example: record via getUserMedia and upload
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
const chunks = [];

recorder.ondataavailable = (e) => chunks.push(e.data);
recorder.onstop = async () => {
  const blob = new Blob(chunks, { type: 'audio/webm' });
  const form = new FormData();
  form.append('file', blob, 'recording.webm');

  await fetch('https://voice-feedback.example.com/api/v1/analyze', {
    method: 'POST',
    body: form,
  });
};

recorder.start();
// ... later:
recorder.stop();
```

### Mobile App

Record audio natively (iOS AVAudioRecorder, Android MediaRecorder, Flutter audio_recorder) and upload the file to the API endpoint.

### Phone System / VoIP

If you use a phone system that supports call recording (e.g., Twilio, Plivo, FreeSWITCH), configure a webhook that uploads the recording to the voice-feedback API after each call ends.

### Video Calls

Most video call tools (Zoom, Google Meet, Microsoft Teams) can export audio recordings. Download the recording and upload it manually or set up an automation.

**Important:** Always get consent before recording. See the DSGVO section below.

---

## 5. Transcription

### Whisper Model Selection

Whisper offers multiple model sizes. Larger models are more accurate but significantly slower:

| Model    | Parameters | Relative Speed | English Accuracy | Multilingual | VRAM    | Recommended For                 |
|----------|-----------|----------------|------------------|--------------|---------|----------------------------------|
| tiny     | 39 M      | ~10x           | Acceptable       | Basic        | ~1 GB   | Quick tests, low-resource         |
| base     | 74 M      | ~7x            | Good             | Good         | ~1 GB   | **Default: good balance**        |
| small    | 244 M     | ~4x            | Very good        | Very good    | ~2 GB   | Production with GPU              |
| medium   | 769 M     | ~2x            | Excellent        | Excellent    | ~5 GB   | High accuracy needs              |
| large-v3 | 1550 M    | 1x (baseline)  | Best             | Best         | ~10 GB  | Maximum accuracy, GPU required   |

**Recommendation:** Start with `base` for development and testing. Use `small` or `medium` in production when accuracy matters. The `large-v3` model is only practical with a dedicated GPU.

### faster-whisper vs openai-whisper

The tool automatically tries `faster-whisper` first and falls back to `openai-whisper`:

| Backend        | Speed     | GPU Support | Installation            |
|----------------|-----------|-------------|-------------------------|
| faster-whisper | 4-8x faster than original | CUDA, CPU | `pip install faster-whisper` |
| openai-whisper | Baseline  | CUDA, CPU   | `pip install openai-whisper` |

For production, `faster-whisper` is strongly recommended.

### Supported Formats

mp3, wav, m4a, ogg, webm, flac, wma -- anything ffmpeg can decode.

---

## 6. Analysis

### What the Tool Extracts

Each transcript is scanned for the following feedback categories:

| Category         | What It Catches                                           | Urgency |
|------------------|-----------------------------------------------------------|---------|
| Feature request  | Wishes, missing functionality, suggestions                | Medium  |
| Bug report       | Errors, crashes, things that do not work                  | High    |
| Pain point       | Confusion, unclear UI, frustration                        | Medium  |
| Praise           | Positive feedback, things that work well                  | Low     |
| Churn risk       | Cancellation intent, competitor mentions, switching plans | Critical|

### Bilingual Support (German + English)

The local analyser understands keyword patterns in both languages. Examples:

**German patterns:**
- Feature request: "waere schoen wenn", "es fehlt", "haette gerne"
- Bug: "funktioniert nicht", "Fehler", "stuerzt ab"
- Confusion: "verstehe nicht", "unklar", "wo finde ich"
- Praise: "super", "toll", "perfekt", "gefaellt mir"
- Churn: "kuendigen", "alternative", "wechseln", "zu teuer"

**English patterns:**
- Feature request: "I wish", "would be nice", "we need"
- Bug: "doesn't work", "broken", "crash", "error"
- Confusion: "confusing", "how do I", "where is"
- Praise: "great", "love it", "works well", "amazing"
- Churn: "cancel", "switch to", "looking at competitors"

### Additional Analysis Output

Beyond individual items, each analysis produces:
- **Overall sentiment** (positive / neutral / negative)
- **Key topics** (extracted by word frequency)
- **Summary** (human-readable overview)
- **Prioritized suggestions** (what to do next)
- **Overall urgency** (low / medium / high / critical)

### Local vs OpenAI Analysis

| Aspect           | Local (rule-based)         | OpenAI (GPT-4)              |
|------------------|----------------------------|-----------------------------|
| Privacy          | All data stays on server   | Transcript sent to OpenAI   |
| Quality          | Good for clear patterns    | Nuanced, contextual         |
| Speed            | Instant                    | 5-15 seconds per transcript |
| Cost             | Free                       | ~$0.01-0.05 per transcript  |
| Languages        | DE + EN patterns           | All languages GPT-4 supports|
| Offline          | Yes                        | No                          |

**Recommendation:** Use local mode by default (privacy, speed, cost). Switch to OpenAI mode when you need higher accuracy on ambiguous feedback or languages beyond German and English.

---

## 7. PostHog Integration

### Events Created

When PostHog sync is enabled, each analysis session creates two types of events:

**`customer_feedback_session`** -- one per session:
```json
{
  "event": "customer_feedback_session",
  "properties": {
    "session_id": "abc123def456",
    "source": "voice-feedback-tool",
    "sentiment": "negative",
    "urgency": "high",
    "topics": ["dashboard", "export", "billing"],
    "summary": "3 bug reports, 2 feature requests, 1 churn risk signal",
    "feature_request_count": 2,
    "bug_report_count": 3,
    "churn_risk_count": 1
  }
}
```

**`customer_feedback_item`** -- one per extracted item:
```json
{
  "event": "customer_feedback_item",
  "properties": {
    "session_id": "abc123def456",
    "item_type": "bug_report",
    "item_quote": "The export function doesn't work",
    "item_urgency": "high",
    "item_tags": ["bug_report", "en", "export"]
  }
}
```

### PostHog Dashboards

Create a PostHog dashboard to visualise feedback data:

| Panel                             | Insight Type | Filter                                      |
|-----------------------------------|-------------|----------------------------------------------|
| Feedback sessions this week       | Trend       | `customer_feedback_session`                  |
| Bug reports trend                 | Trend       | `customer_feedback_item` where `item_type = bug_report` |
| Feature requests by topic         | Table       | `customer_feedback_item` where `item_type = feature_request`, breakdown by `item_tags` |
| Churn risk alerts                 | Trend       | `customer_feedback_item` where `item_type = churn_risk` |
| Sentiment distribution            | Pie chart   | `customer_feedback_session`, breakdown by `sentiment` |
| High-urgency sessions             | Table       | `customer_feedback_session` where `urgency = critical OR high` |

### Annotations

High-urgency sessions (urgency = high or critical) automatically create PostHog annotations. These appear as vertical markers on trend graphs, making it easy to correlate drops in metrics (e.g., retention) with customer feedback signals.

---

## 8. Automated Workflow

### Manual Workflow

```
1. Record customer call (with consent)
2. Upload audio:
   curl -X POST https://voice-feedback.example.com/api/v1/analyze -F "file=@call.m4a"
3. Review results in terminal or PostHog dashboard
```

### Automated Pipeline with n8n

Set up an n8n workflow to auto-process new recordings:

```
Trigger: File created in uploads/ directory (or webhook)
    |
    v
HTTP Request: POST /api/v1/analyze with the audio file
    |
    v
IF urgency == "critical":
    |
    +---> Slack notification to #customer-success
    |
    +---> Create GitHub issue with feedback details
    |
    v
ELSE:
    |
    v
Log to spreadsheet / Notion for weekly review
```

### Webhook Integration

The API can be called from any automation tool. Example triggers:
- **Twilio**: After a call recording is ready, POST the audio URL to the API.
- **Zapier/n8n**: Watch a Dropbox or Google Drive folder for new audio files.
- **CI/CD**: After a release, process recent customer call recordings to check for new issues.
- **Cron job**: Process all files in a directory on a schedule.

```bash
#!/bin/bash
# process-new-recordings.sh -- run via cron every hour
UPLOAD_DIR="/data/recordings/incoming"
API_URL="http://localhost:8000/api/v1/analyze"

for file in "$UPLOAD_DIR"/*.{mp3,m4a,wav,ogg,webm}; do
    [ -f "$file" ] || continue
    echo "Processing: $file"
    curl -s -X POST "$API_URL" -F "file=@$file"
    mv "$file" "$UPLOAD_DIR/processed/"
done
```

---

## 9. DSGVO / Datenschutz

Recording customer conversations has strict legal requirements under the DSGVO (GDPR). Follow these rules:

### Consent

**The customer MUST explicitly consent to being recorded before the conversation starts.** This is non-negotiable.

Acceptable consent methods:
- Verbal consent at the start of the call (with the consent itself on the recording).
- Written consent via email or form before the call.
- In-app consent toggle before starting a recorded session.

Document the consent for each recording. Without documented consent, delete the recording.

### Data Storage

All data stays on your own infrastructure:
- Audio files are stored in `UPLOAD_DIR` on your server.
- Transcripts and analysis results are stored as JSON in `OUTPUT_DIR`.
- PostHog events go to your self-hosted PostHog instance.
- No data is sent to third parties (unless you enable OpenAI analysis mode, in which case only the text transcript is sent to the OpenAI API -- not the audio).

### Data Retention

Set up automatic deletion of audio files after they have been transcribed and analysed:

```bash
# Delete audio files older than 7 days (add to cron)
find /app/uploads -type f -mtime +7 -delete
```

Keep only the analysis results (JSON) for long-term storage. The audio files are no longer needed after transcription.

### PII in Transcripts

Transcripts may contain personal data (names, email addresses, phone numbers). Options:
- Anonymise transcripts before long-term storage (replace names with placeholders).
- Apply data retention policies to session JSON files.
- When using OpenAI analysis mode, be aware that the transcript text is sent to an external API.

### DSGVO Compliance Checklist

| Requirement                                | Implementation                              |
|--------------------------------------------|---------------------------------------------|
| Consent before recording                   | Verbal or written, documented               |
| Data stored on own infrastructure          | Self-hosted (Docker on your server)          |
| Right to deletion                          | Delete audio + JSON for specific customer   |
| Data minimisation                          | Auto-delete audio after analysis            |
| Processing agreement (if using OpenAI)     | OpenAI DPA required                         |
| Documentation                              | Log which recordings were analysed          |

---

## 10. Erweiterungen

### Real-Time Transcription (WebSocket)

Extend the API with a WebSocket endpoint for live transcription during calls:

```
Client streams audio chunks via WebSocket
    |
    v
Server runs Whisper on buffered chunks
    |
    v
Partial transcripts sent back in real time
    |
    v
Full analysis runs when the call ends
```

This requires `faster-whisper` with VAD (voice activity detection) for segment-level streaming.

### Multi-Speaker Detection (Diarization)

Add speaker diarization to distinguish between the customer and your team member:

- Use `pyannote-audio` for speaker diarization.
- Assign each transcript segment to a speaker.
- Analyse only the customer's speech for feedback extraction.

### Trend Analysis Across Sessions

Aggregate analysis results across multiple sessions to identify trends:

- Most requested features this month.
- Bug report frequency over time.
- Sentiment trend (is it improving or declining?).
- Churn risk signal frequency.

Build these trends as PostHog insights using the `customer_feedback_item` events.

### Auto-Create GitHub Issues

For high-urgency items, automatically create GitHub issues:

```python
import httpx

def create_github_issue(item, session_id):
    httpx.post(
        "https://api.github.com/repos/your-org/your-repo/issues",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        json={
            "title": f"[{item.type.value}] {item.text}",
            "body": (
                f"**Source:** Voice feedback session `{session_id}`\n"
                f"**Quote:** {item.quote}\n"
                f"**Urgency:** {item.urgency.value}\n"
                f"**Tags:** {', '.join(item.tags)}"
            ),
            "labels": [item.type.value, f"urgency-{item.urgency.value}"],
        },
    )
```

### Integration with Support Ticket Systems

Connect the analysis output to your support ticket system (Zendesk, Freshdesk, Linear, etc.) to automatically enrich tickets with conversation analysis data or create new tickets from high-urgency items.

---

## 11. Software fragt, Software lernt

This is the overarching concept: your software actively asks users questions, analyses their responses, and uses the answers to improve itself. The voice-feedback tool is one piece of this cycle. Here is the full picture.

### The Concept

Traditional software waits for users to report problems. Modern software proactively gathers feedback through multiple channels and combines it into a single stream of actionable insights.

Three feedback collection methods:

1. **Quantitative (PostHog):** What users do -- page views, clicks, funnels, retention.
2. **Error data (Sentry):** What breaks -- exceptions, crashes, error rates.
3. **Qualitative (Surveys + Conversations):** Why users behave the way they do -- open-ended feedback, feature requests, frustrations.

The power comes from combining all three.

### Flow: PostHog Survey + Analysis + Improvement

```
PostHog Survey (in-app question)
    |
    v
User Response (rating + open text)
    |
    v
Collect responses (PostHog stores them)
    |
    v
Analyse responses (same analyzer as voice-feedback)
    |
    v
Extract patterns:
  - Which features are rated low?
  - What do users wish for?
  - Where are they confused?
    |
    v
Create improvement suggestions
    |
    v
Present to dev team (dashboard + weekly report)
    |
    v
Implement highest-impact improvements
    |
    v
Measure effect (PostHog: did the metric improve?)
```

### Combining Data Sources

Build a combined PostHog dashboard that correlates data from all three sources:

| Data Source                 | PostHog Event                  | What It Tells You                      |
|----------------------------|--------------------------------|----------------------------------------|
| Usage analytics            | `$pageview`, custom events     | What features are used, where drop-off |
| Error tracking             | Sentry webhook to PostHog      | What is broken, how many affected      |
| In-app surveys             | `survey sent`, `survey dismissed` | What users think, NPS score         |
| Customer conversations     | `customer_feedback_session`    | Deep qualitative insights              |
| Customer conversation items| `customer_feedback_item`       | Specific bugs, requests, churn signals |

### Example: Holistic Product Insight

Scenario: your checkout conversion dropped 20% this week.

1. **PostHog funnel** shows the drop-off is between "Enter Payment" and "Complete Purchase".
2. **Sentry** shows a new `TypeError` on the payment page since the last release.
3. **In-app survey** responses from this week mention "payment page not loading".
4. **Customer call analysis** from yesterday: customer said "the payment form is broken, we might switch to [competitor]".

All four data points converge on the same issue. Without the voice-feedback tool, you would have the quantitative signal and the error, but you would miss the churn risk and the customer's emotional context.

### Continuous Learning Loop

```
              +--- Quantitative Data (PostHog) ---+
              |                                    |
              v                                    |
    +------------------+                           |
    |  Product Insight |<-- Error Data (Sentry) ---+
    |    Dashboard     |                           |
    +--------+---------+<-- Qualitative Data ------+
             |              (Surveys + Calls)
             v
    +------------------+
    |  Prioritized     |
    |  Improvement     |
    +--------+---------+
             |
             v
    +------------------+
    |  Ship Change     |
    +--------+---------+
             |
             v
    +------------------+
    |  Measure Impact  |--- feeds back into PostHog
    +------------------+
```

This is the continuous improvement engine: software that asks, learns, and gets better with each iteration. The voice-feedback tool brings the qualitative piece that quantitative tools alone cannot provide.
