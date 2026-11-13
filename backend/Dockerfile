FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN uv pip install --system --no-cache -r /app/backend/pyproject.toml

COPY backend/app /app/backend/app
COPY web /app/web

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "if [ \"${AUTO_UPDATE_YTDLP:-false}\" = \"true\" ]; then pip install --no-cache-dir -U yt-dlp || true; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
