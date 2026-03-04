# ---------------------------------------------------------------------------
# voice-feedback — Multi-stage Docker build
# ---------------------------------------------------------------------------
# Stage 1: Build dependencies
# Stage 2: Runtime image with ffmpeg + Python
# ---------------------------------------------------------------------------

# -- Stage 1: builder -------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tooling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY pyproject.toml .
COPY app/ app/

# Build a wheel so we can install cleanly in the runtime stage
RUN pip wheel --no-cache-dir --wheel-dir /wheels . \
    && pip wheel --no-cache-dir --wheel-dir /wheels \
       faster-whisper openai posthog fastapi "uvicorn[standard]" \
       python-multipart pydantic pydantic-settings rich click httpx


# -- Stage 2: runtime -------------------------------------------------------
FROM python:3.11-slim AS runtime

# ffmpeg is required by Whisper for audio decoding
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pre-built wheels from the builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copy application code
COPY app/ app/

# Create default directories
RUN mkdir -p /app/uploads /app/output

# Environment defaults
ENV WHISPER_MODEL=base \
    ANALYSIS_PROVIDER=local \
    UPLOAD_DIR=/app/uploads \
    OUTPUT_DIR=/app/output \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()"

# Run the API server
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
