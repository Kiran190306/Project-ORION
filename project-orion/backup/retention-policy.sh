#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# Project ORION — Backup Retention Policy Script
# Version: v1.0.0 (EPIC-027 Phase 6C Hardened)
#
# Prunes local backup archives and companion checksums older than
# the retention threshold. Supports dry-run simulation and strict
# error trapping.
# ════════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_BASE="${BACKUP_BASE_DIR:-/var/backups/orion}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
DRY_RUN=false
LOG_FILE=""

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --retention-days|-d)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --base-dir|-b)
            BACKUP_BASE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run, -n           Simulate pruning without deleting files"
            echo "  --retention-days, -d N  Days to retain full backups (default: 7)"
            echo "  --base-dir, -b DIR      Backup directory (default: /var/backups/orion)"
            echo "  --help, -h              Display this help message"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Initialize logging directory
if [ -d "${BACKUP_BASE}" ]; then
    mkdir -p "${BACKUP_BASE}/logs" 2>/dev/null || true
    if [ -w "${BACKUP_BASE}/logs" ]; then
        LOG_FILE="${BACKUP_BASE}/logs/retention-$(date +%Y%m%d_%H%M%S).log"
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

cleanup_trap() {
    local exit_code=$?
    if [ ${exit_code} -ne 0 ]; then
        log "ERROR: Retention policy execution failed with exit code ${exit_code}"
    fi
}
trap cleanup_trap EXIT

apply_retention() {
    local target_dir="$1"
    local pattern="$2"
    local days="$3"
    local label="$4"

    log "Evaluating ${label} retention in: ${target_dir} (older than ${days} days)"

    if [ ! -d "${target_dir}" ]; then
        log "Target directory does not exist, skipping: ${target_dir}"
        return 0
    fi

    # Discover candidate files older than retention days
    local candidates=()
    while IFS= read -r -d '' file; do
        candidates+=("${file}")
    done < <(find "${target_dir}" -maxdepth 3 -type f -name "${pattern}" -mtime +"${days}" -print0 2>/dev/null || true)

    local candidate_count=${#candidates[@]}
    log "Found ${candidate_count} candidate file(s) eligible for pruning."

    if [ ${candidate_count} -eq 0 ]; then
        log "No files eligible for pruning in ${target_dir}"
        return 0
    fi

    for file in "${candidates[@]}"; do
        if [ "${DRY_RUN}" = true ]; then
            log "[DRY-RUN] Would delete: ${file}"
        else
            log "Deleting: ${file}"
            rm -f "${file}"
            # Also clean companion checksum file if it exists
            if [ -f "${file}.sha256" ]; then
                log "Deleting companion checksum: ${file}.sha256"
                rm -f "${file}.sha256"
            fi
        fi
    done

    # Remove empty subdirectories if not dry-run
    if [ "${DRY_RUN}" = false ]; then
        find "${target_dir}" -mindepth 1 -type d -empty -delete 2>/dev/null || true
    fi
}

main() {
    log "=== Project ORION Backup Retention Policy ==="
    log "Base directory: ${BACKUP_BASE}"
    log "Retention threshold: ${RETENTION_DAYS} days"
    log "Dry-run mode: ${DRY_RUN}"

    if [ ! -d "${BACKUP_BASE}" ]; then
        log "Backup base directory not found: ${BACKUP_BASE}. Nothing to prune."
        exit 0
    fi

    # Prune database dumps and companion files
    apply_retention "${BACKUP_BASE}/database" "orion-db-full-*.dump*" "${RETENTION_DAYS}" "PostgreSQL Dumps"

    log "Retention policy completed successfully."
}

main "$@"
