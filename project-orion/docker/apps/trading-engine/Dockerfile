# ════════════════════════════════════════════════════════════
# Project ORION — Trading Engine Production Image
# Multi-stage production container with non-root execution
# ════════════════════════════════════════════════════════════

# ── Stage 1: Build Stage ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root

# ── Stage 2: Production Runtime ──────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="platform-team@orion.example.com"
LABEL service="trading-engine"
LABEL version="0.1.0"
LABEL description="Project ORION Trading Engine ASGI Runtime"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORION_ENVIRONMENT=production \
    ORION_LOG_LEVEL=INFO \
    ORION_SERVER_HOST=0.0.0.0 \
    ORION_SERVER_PORT=8000 \
    PORT=8000 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source and configurations
COPY alembic.ini ./alembic.ini
COPY database ./database
COPY shared ./shared
COPY libraries ./libraries
COPY apps ./apps
COPY scripts ./scripts

# Security: Create and run as non-root user
RUN groupadd -r orion && useradd -r -g orion -d /app -s /sbin/nologin orion && \
    chown -R orion:orion /app

USER orion

EXPOSE 8000

# Health check probing liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/live || exit 1

# Start Trading Engine ASGI application with dynamic PORT binding and POSIX signal propagation
CMD ["sh", "-c", "exec uvicorn apps.trading_engine.src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

