#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# ORION Redis Backup Script
# Version: v0.12.0-alpha.5
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
S3_BUCKET="${BACKUP_S3_BUCKET:-orion-backups}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)
BACKUP_DIR="${BACKUP_BASE}/redis/${DATE_DIR}"
LOG_FILE="${BACKUP_BASE}/logs/redis-backup-${TIMESTAMP}.log"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}" "${BACKUP_BASE}/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
error_exit() { log "ERROR: $*"; exit 1; }

check_prerequisites() {
    command -v redis-cli >/dev/null 2>&1 || error_exit "redis-cli not found"
    command -v gzip >/dev/null 2>&1 || error_exit "gzip not found"
    local auth=""
    [ -n "${REDIS_PASSWORD}" ] && auth="-a ${REDIS_PASSWORD}"
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} ping >/dev/null 2>&1 \
        || error_exit "Cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}"
}

do_redis_backup() {
    local dump_file="orion-redis-${TIMESTAMP}.rdb"
    local filepath="${BACKUP_DIR}/${dump_file}"
    local auth=""
    [ -n "${REDIS_PASSWORD}" ] && auth="-a ${REDIS_PASSWORD}"

    log "Starting Redis backup: ${REDIS_HOST}:${REDIS_PORT}"

    # Trigger BGSAVE and wait for completion
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} BGSAVE >> "${LOG_FILE}" 2>&1
    sleep 2

    # Wait for save to complete
    for i in $(seq 1 30); do
        local save_in_progress=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} \
            INFO persistence 2>/dev/null | grep "rdb_bgsave_in_progress" | cut -d: -f2 | tr -d '\r')
        if [ "${save_in_progress}" = "0" ]; then break; fi
        sleep 1
    done

    # Copy the RDB file
    local rdb_path=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} \
        CONFIG GET dir 2>/dev/null | tail -1 | tr -d '\r')
    local rdb_filename=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} \
        CONFIG GET dbfilename 2>/dev/null | tail -1 | tr -d '\r')
    cp "${rdb_path}/${rdb_filename}" "${filepath}" 2>/dev/null \
        || error_exit "Failed to copy RDB file from ${rdb_path}/${rdb_filename}"

    local file_size=$(stat -c%s "${filepath}" 2>/dev/null || stat -f%z "${filepath}" 2>/dev/null)
    log "RDB file copied: ${filepath} (${file_size} bytes)"

    gzip -9 "${filepath}"
    local compressed="${filepath}.gz"
    log "Compressed: ${compressed}"

    if [ -n "${ENCRYPTION_KEY}" ] && command -v openssl >/dev/null 2>&1; then
        openssl enc -aes-256-cbc -salt -pbkdf2 -in "${compressed}" \
            -out "${compressed}.enc" -pass pass:"${ENCRYPTION_KEY}"
        rm -f "${compressed}"; compressed="${compressed}.enc"
    fi

    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "${compressed}" "s3://${S3_BUCKET}/redis/${DATE_DIR}/" --sse AES256 >> "${LOG_FILE}" 2>&1
    fi
    echo "${compressed}"
}

cleanup_old_backups() {
    log "Running retention cleanup..."
    find "${BACKUP_BASE}/redis" -name "orion-redis-*.rdb.gz*" -type f \
        -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    find "${BACKUP_BASE}/redis" -type d -empty -delete 2>/dev/null || true
    log "Retention cleanup complete"
}

main() {
    log "=== ORION Redis Backup Script ==="
    check_prerequisites
    do_redis_backup
    cleanup_old_backups
    log "Redis backup completed successfully"
}
main "$@"
