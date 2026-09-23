#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Project ORION — Redis Restore Script
# Version: v1.0.0 (EPIC-027 Phase 6C Hardened)
#
# NOTICE: DEPRECATED FOR MANAGED CLOUD PAAS (RENDER CLOUD)
#
# Architectural Truth:
# Redis in Project ORION operates exclusively as an in-memory
# cache, rate limiter sliding-window counter store, and pub/sub bus.
# It holds $0.00 persistent financial state.
#
# On managed cloud Redis (e.g. Render Redis), client containers have
# no server filesystem access, and administrative commands like
# SHUTDOWN NOSAVE and file copying to /var/lib/redis are restricted.
#
# Production Cloud Recovery:
# In case of cloud Redis failure, restart the service:
#   render services restart orion-redis
# The application rate limiter falls back automatically to local
# memory, and caches warm up cleanly from live broker streams.
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
RESTORE_FILE="${1:-}"
LOG_FILE=""

if [ -d "${BACKUP_BASE}" ]; then
    mkdir -p "${BACKUP_BASE}/logs" 2>/dev/null || true
    if [ -w "${BACKUP_BASE}/logs" ]; then
        LOG_FILE="${BACKUP_BASE}/logs/restore-redis-$(date +%Y%m%d_%H%M%S).log"
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

    if [ -z "${RESTORE_FILE}" ]; then
        echo "Usage: $0 <backup-file.rdb>"
        echo ""
        echo "Notice: This script is for local standalone Docker development only."
        echo "For Render Cloud Redis, perform service restart via 'render services restart orion-redis'."
        exit 1
    fi

    if [ -n "${REDIS_PASSWORD}" ]; then
        export REDISCLI_AUTH="${REDIS_PASSWORD}"
    fi
}

do_restore() {
    local restore_path="${RESTORE_FILE}"
    [ -f "${restore_path}" ] || error_exit "Backup file not found: ${restore_path}"

    log "NOTICE: Local Redis restore invoked for: ${restore_path}"

    # Get local Redis server directories if accessible
    local rdb_dir
    local rdb_filename
    rdb_dir=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET dir 2>/dev/null | tail -1 | tr -d '\r') || true
    rdb_filename=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET dbfilename 2>/dev/null | tail -1 | tr -d '\r') || true

    if [ -n "${rdb_dir}" ] && [ -n "${rdb_filename}" ] && [ -d "${rdb_dir}" ]; then
        log "Stopping local Redis daemon..."
        redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" SHUTDOWN NOSAVE >/dev/null 2>&1 || true
        sleep 2

        log "Copying RDB file to ${rdb_dir}/${rdb_filename}..."
        cp "${restore_path}" "${rdb_dir}/${rdb_filename}"
        chmod 0640 "${rdb_dir}/${rdb_filename}" 2>/dev/null || true
        log "RDB file copied. Restart local Redis service to load restored state."
    else
        log "WARNING: Server filesystem path not accessible. On managed cloud Redis, use service restart instead."
    fi
}

main() {
    log "=== Project ORION Redis Restore (Local Dev Only) ==="
    check_prerequisites
    do_restore
    log "Redis restore routine finished."
}

main "$@"
