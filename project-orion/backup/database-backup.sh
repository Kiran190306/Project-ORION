#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Project ORION — Database Backup Script
# Version: v1.0.0 (EPIC-027 Phase 6C Hardened)
#
# Generates deterministic, custom-format PostgreSQL logical dumps
# with cryptographic SHA-256 checksum sidecars, TOC verification,
# and safe environment-based AES-256 encryption.
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-orion_prod}"
DB_USER="${DB_USER:-orion}"
DB_PASSWORD="${DB_PASSWORD:-}"
DATABASE_URL="${ORION_DATABASE_URL:-${DATABASE_URL:-}}"
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)
OUTPUT_DIR="${BACKUP_BASE}/database/${DATE_DIR}"
LOG_FILE=""
TEMP_FILE=""

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --output-dir, -o DIR  Output directory for dump artifacts"
            echo "  --help, -h            Display this help message"
            echo ""
            echo "Environment Variables:"
            echo "  ORION_DATABASE_URL    Database connection URL (takes precedence)"
            echo "  DB_HOST, DB_PORT      PostgreSQL connection target (default: localhost:5432)"
            echo "  DB_NAME, DB_USER      Database and username (default: orion_prod, orion)"
            echo "  DB_PASSWORD           Authentication password (passed securely via PGPASSWORD)"
            echo "  BACKUP_ENCRYPTION_KEY Optional AES-256 encryption key (passed via env:VAR)"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

mkdir -p "${OUTPUT_DIR}" 2>/dev/null || true
if [ -d "${BACKUP_BASE}" ]; then
    mkdir -p "${BACKUP_BASE}/logs" 2>/dev/null || true
    if [ -w "${BACKUP_BASE}/logs" ]; then
        LOG_FILE="${BACKUP_BASE}/logs/database-backup-${TIMESTAMP}.log"
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

cleanup_on_exit() {
    local exit_code=$?
    if [ ${exit_code} -ne 0 ]; then
        log "ERROR: Backup script failed with exit code ${exit_code}"
        if [ -n "${TEMP_FILE}" ] && [ -f "${TEMP_FILE}" ]; then
            log "Cleaning up incomplete artifact: ${TEMP_FILE}"
            rm -f "${TEMP_FILE}" "${TEMP_FILE}.sha256" 2>/dev/null || true
        fi
    fi
}
trap cleanup_on_exit EXIT

check_prerequisites() {
    if ! command -v pg_dump >/dev/null 2>&1; then
        for cand in "/c/Program Files/PostgreSQL"/*/bin /usr/lib/postgresql/*/bin; do
            if [ -d "${cand}" ]; then
                export PATH="${cand}:${PATH}"
                break
            fi
        done
    fi

    command -v pg_dump >/dev/null 2>&1 || error_exit "pg_dump not found in PATH"
    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found in PATH"

    # Check sha256sum or shasum
    if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
        error_exit "Neither sha256sum nor shasum found in PATH"
    fi

    # Set up PostgreSQL authentication environment variable
    if [ -n "${DB_PASSWORD}" ]; then
        export PGPASSWORD="${DB_PASSWORD}"
    fi
}

compute_sha256() {
    local target="$1"
    local output_file="$2"
    local dir
    dir=$(dirname "${target}")
    local base
    base=$(basename "${target}")
    if command -v sha256sum >/dev/null 2>&1; then
        (cd "${dir}" && sha256sum "${base}") > "${output_file}"
    else
        (cd "${dir}" && shasum -a 256 "${base}") > "${output_file}"
    fi
}

do_backup() {
    local dump_filename="orion-db-full-${TIMESTAMP}.dump"
    local dump_filepath="${OUTPUT_DIR}/${dump_filename}"
    TEMP_FILE="${dump_filepath}"

    log "Starting logical database dump..."

    # Execute pg_dump using custom format (-Fc) WITHOUT incompatible parallel flag (-j)
    # Using --no-owner and --no-privileges ensures portability to unprivileged managed cloud targets.
    if [ -n "${DATABASE_URL}" ]; then
        log "Connecting via connection string (credentials masked in logs)"
        pg_dump -Fc --no-owner --no-privileges --dbname="${DATABASE_URL}" -f "${dump_filepath}"
    else
        log "Target: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        pg_dump -Fc --no-owner --no-privileges -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${dump_filepath}"
    fi

    local dump_size
    dump_size=$(wc -c < "${dump_filepath}" | tr -d ' ')
    log "Dump completed: ${dump_filepath} (${dump_size} bytes)"

    # Archive Table-of-Contents Verification
    log "Verifying archive table-of-contents via pg_restore --list..."
    pg_restore -l "${dump_filepath}" >/dev/null 2>&1 || error_exit "Archive TOC verification failed for ${dump_filepath}"
    log "Archive TOC verification passed."

    # Compute SHA-256 Checksum Sidecar
    local sha256_file="${dump_filepath}.sha256"
    compute_sha256 "${dump_filepath}" "${sha256_file}"
    local hash_val
    hash_val=$(cut -d' ' -f1 < "${sha256_file}")
    log "SHA-256 sidecar created: ${sha256_file} (${hash_val})"

    # Restrict permissions
    chmod 0600 "${dump_filepath}" "${sha256_file}" 2>/dev/null || true

    local final_artifact="${dump_filepath}"

    # Optional AES-256-CBC Encryption via environment variable (Never passed on CLI)
    if [ -n "${BACKUP_ENCRYPTION_KEY}" ]; then
        if command -v openssl >/dev/null 2>&1; then
            log "Encrypting backup archive with AES-256-CBC (PBKDF2) via -pass env:VAR..."
            local enc_filepath="${dump_filepath}.enc"
            openssl enc -aes-256-cbc -salt -pbkdf2 -in "${dump_filepath}" -out "${enc_filepath}" -pass env:BACKUP_ENCRYPTION_KEY
            chmod 0600 "${enc_filepath}" 2>/dev/null || true

            # Compute SHA-256 for the encrypted artifact
            local enc_sha256_file="${enc_filepath}.sha256"
            compute_sha256 "${enc_filepath}" "${enc_sha256_file}"
            log "Encrypted artifact created: ${enc_filepath}"

            # Remove unencrypted dump and update final artifact
            rm -f "${dump_filepath}" "${sha256_file}"
            final_artifact="${enc_filepath}"
            TEMP_FILE="${final_artifact}"
        else
            log "WARNING: BACKUP_ENCRYPTION_KEY is set but openssl is not installed. Archive left unencrypted."
        fi
    fi

    TEMP_FILE=""
    log "SUCCESS: Backup artifact generated: ${final_artifact}"
    echo "${final_artifact}"
}

main() {
    log "=== Project ORION Database Backup Script ==="
    check_prerequisites
    do_backup
    log "Backup completed successfully."
}

main "$@"
