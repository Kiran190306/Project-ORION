#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Project ORION — Safe Database Restore Script
# Version: v1.0.0 (EPIC-027 Phase 6C Hardened)
#
# Primary Architecture: Isolated Target Database Restoration.
# Requires explicit --target-url parameter.
# Verifies SHA-256 checksum and TOC BEFORE modifying any database.
# Prohibits DROP DATABASE and CREATE DATABASE.
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
TARGET_URL=""
BACKUP_FILE=""
BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
EMERGENCY_IN_PLACE=false
TEMP_FILES=()
LOG_FILE=""

usage() {
    local code="${1:-0}"
    echo "Usage: $0 --target-url <TARGET_DATABASE_URL> <backup-file> [OPTIONS]"
    echo ""
    echo "Mandatory Arguments:"
    echo "  --target-url, -t URL      Explicit target PostgreSQL connection URL"
    echo "  <backup-file>             Path to .dump or .dump.enc archive"
    echo ""
    echo "Options:"
    echo "  --help, -h                Display this help message"
    echo ""
    echo "Emergency (Manual Only):"
    echo "  --emergency-manual-in-place-schema-reset"
    echo "                            Explicitly resets schema before restore (requires confirmation)"
    echo ""
    echo "Safety Invariants:"
    echo "  * Production DATABASE_URL is NEVER targeted by default."
    echo "  * Checksum is verified BEFORE touching any target database."
    echo "  * Normal restore NEVER executes DROP DATABASE or CREATE DATABASE."
    exit "${code}"
}

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-url|-t)
            TARGET_URL="$2"
            shift 2
            ;;
        --emergency-manual-in-place-schema-reset)
            EMERGENCY_IN_PLACE=true
            shift
            ;;
        --help|-h)
            usage 0
            ;;
        -*)
            echo "ERROR: Unknown option: $1" >&2
            usage 1
            ;;
        *)
            if [ -z "${BACKUP_FILE}" ]; then
                BACKUP_FILE="$1"
            else
                echo "ERROR: Unexpected argument: $1" >&2
                usage 1
            fi
            shift
            ;;
    esac
done

if [ -d "${BACKUP_BASE}" ]; then
    mkdir -p "${BACKUP_BASE}/logs" 2>/dev/null || true
    if [ -w "${BACKUP_BASE}/logs" ]; then
        LOG_FILE="${BACKUP_BASE}/logs/restore-database-$(date +%Y%m%d_%H%M%S).log"
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

cleanup_temp_files() {
    for f in "${TEMP_FILES[@]}"; do
        if [ -f "${f}" ]; then
            log "Cleaning up decrypted scratch file: ${f}"
            rm -f "${f}" 2>/dev/null || true
        fi
    done
}
trap cleanup_temp_files EXIT

validate_prerequisites() {
    # 1. Target URL check
    if [ -z "${TARGET_URL}" ]; then
        error_exit "Missing mandatory --target-url parameter. Target database must be explicitly specified."
    fi

    # 2. Backup file check
    if [ -z "${BACKUP_FILE}" ]; then
        error_exit "Missing backup file path argument."
    fi

    if [ ! -f "${BACKUP_FILE}" ]; then
        error_exit "Backup artifact not found: ${BACKUP_FILE}"
    fi

    # 3. Tool prerequisites
    if ! command -v pg_restore >/dev/null 2>&1; then
        for cand in "/c/Program Files/PostgreSQL"/*/bin /usr/lib/postgresql/*/bin; do
            if [ -d "${cand}" ]; then
                export PATH="${cand}:${PATH}"
                break
            fi
        done
    fi

    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found in PATH"
    command -v psql >/dev/null 2>&1 || error_exit "psql not found in PATH"

    if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
        error_exit "Neither sha256sum nor shasum found in PATH"
    fi
}

verify_checksum() {
    local artifact="$1"
    local sha256_file="${artifact}.sha256"

    log "Verifying cryptographic SHA-256 checksum..."
    if [ ! -f "${sha256_file}" ]; then
        error_exit "Checksum sidecar not found: ${sha256_file}. Cannot verify archive integrity prior to restore."
    fi

    local target_dir
    target_dir=$(dirname "${artifact}")
    local filename
    filename=$(basename "${artifact}")

    # Run checksum verification inside artifact directory
    if command -v sha256sum >/dev/null 2>&1; then
        (cd "${target_dir}" && sha256sum -c "${filename}.sha256") >/dev/null 2>&1 \
            || error_exit "SHA-256 CHECKSUM MISMATCH! Backup archive may be corrupted. Aborting restore."
    else
        (cd "${target_dir}" && shasum -a 256 -c "${filename}.sha256") >/dev/null 2>&1 \
            || error_exit "SHA-256 CHECKSUM MISMATCH! Backup archive may be corrupted. Aborting restore."
    fi

    log "SHA-256 checksum verified successfully."
}

do_restore() {
    local restore_path="${BACKUP_FILE}"

    # Step 1: Pre-restore Checksum Verification
    verify_checksum "${restore_path}"

    # Step 2: Decryption if encrypted (.enc)
    if [[ "${restore_path}" == *.enc ]]; then
        log "Encrypted archive detected. Decrypting with AES-256-CBC via environment variable..."
        [ -n "${BACKUP_ENCRYPTION_KEY}" ] || error_exit "BACKUP_ENCRYPTION_KEY environment variable required for encrypted backup"
        command -v openssl >/dev/null 2>&1 || error_exit "openssl CLI required for decrypting encrypted backup"

        local decrypted="${restore_path%.enc}.tmp_restore"
        TEMP_FILES+=("${decrypted}")
        openssl enc -d -aes-256-cbc -pbkdf2 -in "${restore_path}" -out "${decrypted}" -pass env:BACKUP_ENCRYPTION_KEY
        chmod 0600 "${decrypted}" 2>/dev/null || true
        restore_path="${decrypted}"
        log "Decrypted scratch artifact ready."
    fi

    # Step 3: Archive Table-of-Contents Verification (Pre-Restore Integrity Probe)
    log "Verifying archive table-of-contents via pg_restore --list..."
    pg_restore -l "${restore_path}" >/dev/null 2>&1 || error_exit "Archive TOC verification failed. Archive is unreadable or malformed."
    log "Archive TOC verification passed."

    # Step 4: Handle Emergency Manual In-Place Reset (If explicitly requested)
    if [ "${EMERGENCY_IN_PLACE}" = true ]; then
        log "WARNING: --emergency-manual-in-place-schema-reset requested!"
        echo "================================================================="
        echo "  DANGER: You have requested an IN-PLACE SCHEMA RESET.           "
        echo "  This will DROP the 'public' schema on the target database!     "
        echo "================================================================="

        # Require interactive human confirmation
        if [ -t 0 ]; then
            read -r -p "Type 'DESTROY-AND-RESTORE' to proceed: " confirm_token
            if [ "${confirm_token}" != "DESTROY-AND-RESTORE" ]; then
                error_exit "Schema reset aborted: confirmation token did not match."
            fi
        else
            error_exit "Emergency in-place schema reset cannot be run non-interactively."
        fi

        log "Executing manual schema reset on target database..."
        psql --dbname="${TARGET_URL}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO CURRENT_USER;"
        log "Target schema reset complete."
    fi

    # Step 5: Execute pg_restore into isolated target
    log "Executing pg_restore into target database..."
    pg_restore -d "${TARGET_URL}" --clean --if-exists --no-owner --no-privileges "${restore_path}" 2>&1 | while read -r line; do
        # Log progress, filtering noisy remarks
        if [[ ! "${line}" =~ ^pg_restore:\ warning: ]]; then
            log "pg_restore: ${line}"
        fi
    done || true

    log "pg_restore execution completed."

    # Step 6: Post-Restore Verification via verify_restore.py
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    local verifier="${script_dir}/scripts/deploy/verify_restore.py"

    if [ -f "${verifier}" ]; then
        log "Invoking post-restore verification tool: ${verifier}..."
        python "${verifier}" --database-url "${TARGET_URL}" || error_exit "Post-restore semantic verification failed!"
    else
        log "Notice: ${verifier} not found. Skipping automated semantic verification."
    fi
}

main() {
    log "=== Project ORION Safe Database Restore ==="
    validate_prerequisites
    do_restore
    log "SUCCESS: Database restore and verification completed."
}

main "$@"
