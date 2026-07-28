#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# ORION Database Restore Script
# Version: v0.12.0-alpha.5
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-orion}"
DB_USER="${DB_USER:-orion}"
DB_PASSWORD="${DB_PASSWORD:-}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
RESTORE_FILE="${1:-}"
LOG_FILE="${BACKUP_BASE}/logs/restore-database-$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${BACKUP_BASE}/logs"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
error_exit() { log "ERROR: $*"; exit 1; }

check_prerequisites() {
    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found"
    command -v psql >/dev/null 2>&1 || error_exit "psql not found"
    if [ -n "${DB_PASSWORD}" ]; then export PGPASSWORD="${DB_PASSWORD}"; fi
    if [ -z "${RESTORE_FILE}" ]; then
        log "Available backups:"
        ls -1 "${BACKUP_BASE}/database/"*/orion-db-full-*.dump.gz* 2>/dev/null || echo "No backups found"
        error_exit "Usage: $0 <backup-file>"
    fi
}

do_restore() {
    local restore_path="${RESTORE_FILE}"
    log "Starting database restore from: ${restore_path}"

    [ -f "${restore_path}" ] || error_exit "Backup file not found: ${restore_path}"

    # Decrypt if encrypted
    if [[ "${restore_path}" == *.enc ]]; then
        [ -n "${ENCRYPTION_KEY}" ] || error_exit "ENCRYPTION_KEY required for encrypted backup"
        local decrypted="${restore_path%.enc}"
        openssl enc -d -aes-256-cbc -pbkdf2 -in "${restore_path}" \
            -out "${decrypted}" -pass pass:"${ENCRYPTION_KEY}"
        restore_path="${decrypted}"
        log "Decrypted: ${restore_path}"
    fi

    # Decompress if gzipped
    if [[ "${restore_path}" == *.gz ]]; then
        local decompressed="${restore_path%.gz}"
        gunzip -c "${restore_path}" > "${decompressed}"
        restore_path="${decompressed}"
        log "Decompressed: ${restore_path}"
    fi

    # Drop existing connections and restore
    log "Terminating existing connections to ${DB_NAME}..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
        >> "${LOG_FILE}" 2>&1 || true

    log "Dropping and recreating database ${DB_NAME}..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" >> "${LOG_FILE}" 2>&1
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "CREATE DATABASE ${DB_NAME};" >> "${LOG_FILE}" 2>&1

    log "Restoring from dump..."
    pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -j 4 --verbose "${restore_path}" 2>&1 | tee -a "${LOG_FILE}"

    log "Database restore completed successfully"

    # Cleanup decompressed/decrypted files
    if [ "${restore_path}" != "${RESTORE_FILE}" ]; then
        rm -f "${restore_path}"
    fi
}

verify_restore() {
    log "Verifying restore..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" \
        2>&1 | tee -a "${LOG_FILE}"
    log "Restore verification complete"
}

main() {
    log "=== ORION Database Restore Script ==="
    check_prerequisites
    do_restore
    verify_restore
    log "Restore completed successfully"
}
main "$@"
