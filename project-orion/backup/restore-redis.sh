#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# ORION Redis Restore Script
# Version: v0.12.0-alpha.5
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
RESTORE_FILE="${1:-}"
LOG_FILE="${BACKUP_BASE}/logs/restore-redis-$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${BACKUP_BASE}/logs"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
error_exit() { log "ERROR: $*"; exit 1; }

check_prerequisites() {
    command -v redis-cli >/dev/null 2>&1 || error_exit "redis-cli not found"
    if [ -z "${RESTORE_FILE}" ]; then
        log "Available backups:"
        ls -1 "${BACKUP_BASE}/redis/"*/orion-redis-*.rdb.gz* 2>/dev/null || echo "No backups found"
        error_exit "Usage: $0 <backup-file>"
    fi
}

do_restore() {
    local restore_path="${RESTORE_FILE}"
    local auth=""
    [ -n "${REDIS_PASSWORD}" ] && auth="-a ${REDIS_PASSWORD}"

    log "Starting Redis restore from: ${restore_path}"
    [ -f "${restore_path}" ] || error_exit "Backup file not found: ${restore_path}"

    # Decrypt
    if [[ "${restore_path}" == *.enc ]]; then
        [ -n "${ENCRYPTION_KEY}" ] || error_exit "ENCRYPTION_KEY required"
        local decrypted="${restore_path%.enc}"
        openssl enc -d -aes-256-cbc -pbkdf2 -in "${restore_path}" \
            -out "${decrypted}" -pass pass:"${ENCRYPTION_KEY}"
        restore_path="${decrypted}"
    fi

    # Decompress
    if [[ "${restore_path}" == *.gz ]]; then
        local decompressed="${restore_path%.gz}"
        gunzip -c "${restore_path}" > "${decompressed}"
        restore_path="${decompressed}"
    fi

    # Get Redis config for RDB path
    local rdb_dir=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} \
        CONFIG GET dir 2>/dev/null | tail -1 | tr -d '\r')
    local rdb_filename=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} \
        CONFIG GET dbfilename 2>/dev/null | tail -1 | tr -d '\r')

    log "Stopping Redis to copy RDB file..."
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth} SHUTDOWN NOSAVE >> "${LOG_FILE}" 2>&1 || true
    sleep 2

    log "Copying RDB file to ${rdb_dir}/${rdb_filename}..."
    cp "${restore_path}" "${rdb_dir}/${rdb_filename}"
    chmod 640 "${rdb_dir}/${rdb_filename}"

    log "Redis restore file placed. Restart Redis service manually to complete restore."
    log "Restore completed. File: ${rdb_dir}/${rdb_filename}"

    # Cleanup
    if [ "${restore_path}" != "${RESTORE_FILE}" ]; then rm -f "${restore_path}"; fi
}

main() {
    log "=== ORION Redis Restore Script ==="
    check_prerequisites
    do_restore
    log "Redis restore prepared — restart Redis to apply"
}
main "$@"
