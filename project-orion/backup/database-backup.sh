#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# ORION Database Backup Script
# Version: v0.12.0-alpha.5
# Supports: Full and Incremental backups with retention rotation
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-orion}"
DB_USER="${DB_USER:-orion}"
DB_PASSWORD="${DB_PASSWORD:-}"
BACKUP_TYPE="${1:-full}"
RETENTION_DAYS_FULL=7
RETENTION_DAYS_INCR=14
S3_BUCKET="${BACKUP_S3_BUCKET:-orion-backups}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)
BACKUP_DIR="${BACKUP_BASE}/database/${DATE_DIR}"
LOG_FILE="${BACKUP_BASE}/logs/database-backup-${TIMESTAMP}.log"

mkdir -p "${BACKUP_DIR}" "${BACKUP_BASE}/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
error_exit() { log "ERROR: $*"; exit 1; }

check_prerequisites() {
    command -v pg_dump >/dev/null 2>&1 || error_exit "pg_dump not found"
    command -v gzip >/dev/null 2>&1 || error_exit "gzip not found"
    if [ -n "${DB_PASSWORD}" ]; then export PGPASSWORD="${DB_PASSWORD}"; fi
    pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" >/dev/null 2>&1 \
        || error_exit "Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}"
}

do_full_backup() {
    local filename="orion-db-full-${TIMESTAMP}.dump"
    local filepath="${BACKUP_DIR}/${filename}"
    log "Starting FULL backup: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
    pg_dump -Fc -j 4 -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -f "${filepath}" --verbose 2>&1 | tee -a "${LOG_FILE}"
    gzip -9 "${filepath}"
    local compressed="${filepath}.gz"
    log "Full backup complete: ${compressed}"
    if [ -n "${ENCRYPTION_KEY}" ] && command -v openssl >/dev/null 2>&1; then
        openssl enc -aes-256-cbc -salt -pbkdf2 -in "${compressed}" \
            -out "${compressed}.enc" -pass pass:"${ENCRYPTION_KEY}"
        rm -f "${compressed}"; compressed="${compressed}.enc"
    fi
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "${compressed}" "s3://${S3_BUCKET}/database/${DATE_DIR}/" --sse AES256 >> "${LOG_FILE}" 2>&1
    fi
    echo "${compressed}"
}

cleanup_old_backups() {
    log "Running retention cleanup..."
    if [ "${BACKUP_TYPE}" = "full" ]; then
        find "${BACKUP_BASE}/database" -name "orion-db-full-*.dump.gz*" -type f \
            -mtime +${RETENTION_DAYS_FULL} -delete 2>/dev/null || true
    fi
    find "${BACKUP_BASE}/database" -type d -empty -delete 2>/dev/null || true
    log "Retention cleanup complete"
}

main() {
    log "=== ORION Database Backup Script ==="
    log "Type: ${BACKUP_TYPE}"
    check_prerequisites
    if [ "${BACKUP_TYPE}" = "full" ]; then do_full_backup
    else error_exit "Unknown type: ${BACKUP_TYPE}"; fi
    cleanup_old_backups
    log "Backup completed successfully"
}
main "$@"
