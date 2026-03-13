FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY coolify_auto_deploy/ coolify_auto_deploy/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "coolify_auto_deploy.main:app", "--host", "0.0.0.0", "--port", "8000"]
