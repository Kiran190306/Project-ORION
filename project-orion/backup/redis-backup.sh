#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Project ORION — Redis Backup Script
# Version: v1.0.0 (EPIC-027 Phase 6C Hardened)
#
# NOTICE: DEPRECATED FOR MANAGED CLOUD PAAS (RENDER CLOUD)
#
# Architectural Truth:
# According to Project ORION's domain architecture, Redis holds
# strictly ephemeral cache data, sliding-window rate limit counters,
# and pub/sub message queues ($0.00 persistent financial state).
# All accounts, orders, positions, and balances reside in PostgreSQL.
#
# On managed cloud Redis (e.g. Render Redis), client containers have
# no server filesystem access, and administrative commands like
# CONFIG GET are restricted. This script is retained ONLY for local
# standalone Docker container development environments.
#
# Production Cloud Recovery:
# In case of cloud Redis failure, restart the service:
#   render services restart orion-redis
# Caches will re-warm automatically from incoming quote feeds.
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)
BACKUP_DIR="${BACKUP_BASE}/redis/${DATE_DIR}"
LOG_FILE=""
RETENTION_DAYS=7

if [ -d "${BACKUP_BASE}" ]; then
    mkdir -p "${BACKUP_DIR}" "${BACKUP_BASE}/logs" 2>/dev/null || true
    if [ -w "${BACKUP_BASE}/logs" ]; then
        LOG_FILE="${BACKUP_BASE}/logs/redis-backup-${TIMESTAMP}.log"
    fi
fi

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "${msg}"
    if [ -n "${LOG_FILE}" ] && [ -w "${LOG_FILE}" ]; then
        echo "${msg}" >> "${LOG_FILE}"
    fi
}

error_exit() {
    log "ERROR: $*"
    exit 1
}

check_prerequisites() {
    command -v redis-cli >/dev/null 2>&1 || error_exit "redis-cli not found in PATH"

    # Tool-native authentication avoiding CLI argument password leaks
    if [ -n "${REDIS_PASSWORD}" ]; then
        export REDISCLI_AUTH="${REDIS_PASSWORD}"
    fi

    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping >/dev/null 2>&1 \
        || error_exit "Cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}"
}

do_redis_backup() {
    local dump_file="orion-redis-${TIMESTAMP}.rdb"
    local filepath="${BACKUP_DIR}/${dump_file}"

    log "NOTICE: Executing local Redis backup. Not applicable to managed cloud Redis."
    log "Starting Redis snapshot trigger: ${REDIS_HOST}:${REDIS_PORT}"

    # Trigger BGSAVE
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" BGSAVE >/dev/null 2>&1 || true
    sleep 2

    # Wait for save completion (timeout 30s)
    local save_in_progress="1"
    for _ in $(seq 1 30); do
        save_in_progress=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" \
            INFO persistence 2>/dev/null | grep "rdb_bgsave_in_progress" | cut -d: -f2 | tr -d '\r')
        if [ "${save_in_progress}" = "0" ]; then
            break
        fi
        sleep 1
    done

    # Fetch RDB path from Redis configuration (local development only)
    local rdb_path
    local rdb_filename
    rdb_path=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET dir 2>/dev/null | tail -1 | tr -d '\r') || true
    rdb_filename=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET dbfilename 2>/dev/null | tail -1 | tr -d '\r') || true

    if [ -n "${rdb_path}" ] && [ -n "${rdb_filename}" ] && [ -f "${rdb_path}/${rdb_filename}" ]; then
        cp "${rdb_path}/${rdb_filename}" "${filepath}"
        local file_size
        file_size=$(wc -c < "${filepath}" | tr -d ' ')
        log "RDB file copied successfully: ${filepath} (${file_size} bytes)"

        # Generate checksum sidecar
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum "${filepath}" > "${filepath}.sha256"
        fi
    else
        log "WARNING: Could not access host RDB file. On managed cloud Redis, host filesystem access is restricted."
    fi
}

main() {
    log "=== Project ORION Redis Backup (Local Dev Only) ==="
    check_prerequisites
    do_redis_backup
    log "Redis backup routine finished."
}

main "$@"
