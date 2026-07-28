# ════════════════════════════════════════════════════════════
# ORION Production Base Image
# Version: 0.12.0-alpha.4
# ════════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

LABEL maintainer="platform-team@orion.example.com"
LABEL version="0.12.0-alpha.4"
LABEL org.opencontainers.image.source="https://github.com/orion/trading-platform"
LABEL org.opencontainers.image.description="ORION Enterprise Trading Platform"
LABEL org.opencontainers.image.licenses="MIT"

# ── System Dependencies ────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Python Environment ────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── Common Utilities ──────────────────────────────────────
COPY scripts/build/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ── Health Check ──────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Security: Run as non-root ────────────────────────────
RUN groupadd -r orion && useradd -r -g orion -d /app -s /sbin/nologin orion
USER orion

ENTRYPOINT ["/entrypoint.sh"]


# ════════════════════════════════════════════════════════════
# Development Stage
# ════════════════════════════════════════════════════════════
FROM base AS development

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*
USER orion

COPY --chown=orion:orion pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install

COPY --chown=orion:orion . .


# ════════════════════════════════════════════════════════════
# Production Stage
# ════════════════════════════════════════════════════════════
FROM base AS production

COPY --chown=orion:orion --from=development /app /app

RUN pip install poetry && \
    poetry install --only main --no-interaction --no-ansi && \
    pip uninstall poetry -y && \
    rm -rf ~/.cache/pip

USER orion
CMD ["python"]

