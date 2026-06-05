#!/usr/bin/env bash
# =============================================================================
# SilverTrade PostgreSQL Backup & PITR Configurator
# =============================================================================
# Handles:
#   1. Logical dumps (pg_dump) for all 5 databases: silvertrade, logs, latency,
#      health, sandbox
#   2. WAL archiving configuration template for Point-in-Time Recovery
#   3. Retention policy: daily dumps kept for 7 days, weekly for 30 days
#   4. Optional S3/GCS upload (via rclone or aws cli)
#
# Usage:
#   # Full logical dump of all databases (default)
#   bash scripts/pg_backup.sh
#
#   # Dump a single database
#   bash scripts/pg_backup.sh --db=silvertrade
#
#   # Dry-run (show what would be done)
#   bash scripts/pg_backup.sh --dry-run
#
#   # Generate WAL archiving config snippet (for postgresql.conf)
#   bash scripts/pg_backup.sh --show-pitr-config
#
#   # Restore from latest dump
#   bash scripts/pg_backup.sh --restore=silvertrade
#
#   # List available backups
#   bash scripts/pg_backup.sh --list
#
# Dependencies:
#   - pg_dump / pg_restore (PostgreSQL client tools)
#   - Optional: aws cli or rclone for remote upload
#
# Environment variables (read from .env or export before running):
#   PG_HOST          — PostgreSQL host (default: 127.0.0.1)
#   PG_PORT          — PostgreSQL port (default: 5432)
#   PG_USER          — PostgreSQL user (default: silvertrade)
#   PG_PASSWORD      — PostgreSQL password (default: silvertrade)
#   BACKUP_DIR       — Local backup directory (default: ./backups/pg)
#   BACKUP_RETENTION_DAYS — Daily dump retention (default: 7)
#   BACKUP_RETENTION_WEEKLY — Weekly dump retention (default: 30)
#   BACKUP_S3_PATH   — Optional S3/GCS path for remote upload (e.g. s3://bucket/silvertrade-backups)
#   RCLONE_REMOTE    — Optional rclone remote name (if using rclone instead of aws)
# =============================================================================

set -euo pipefail

# ── Colors & formatting ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Colour
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Configuration ────────────────────────────────────────────────────────────
# Load env vars from .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
[ -f "$ENV_FILE" ] && set -a && source "$ENV_FILE" && set +a

PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-silvertrade}"
PG_PASSWORD="${PG_PASSWORD:-silvertrade}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups/pg}"
RETENTION_DAILY="${BACKUP_RETENTION_DAYS:-7}"
RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-30}"
DRY_RUN="${DRY_RUN:-false}"

# All databases managed by the platform
DATABASES=("silvertrade" "logs" "latency" "health" "sandbox")

# ── Helpers ──────────────────────────────────────────────────────────────────

export PGPASSWORD="$PG_PASSWORD"

pg_dump_cmd() {
    local db="$1" output="$2"
    shift 2
    pg_dump \
        -h "$PG_HOST" \
        -p "$PG_PORT" \
        -U "$PG_USER" \
        -d "$db" \
        --format=custom \
        --compress=9 \
        --verbose \
        --file="$output" \
        "$@"
}

pg_restore_cmd() {
    local db="$1" input="$2"
    shift 2
    pg_restore \
        -h "$PG_HOST" \
        -p "$PG_PORT" \
        -U "$PG_USER" \
        -d "$db" \
        --clean \
        --if-exists \
        --verbose \
        "$input" \
        "$@"
}

timestamp() {
    date +"%Y%m%d_%H%M%S"
}

# ── Actions ──────────────────────────────────────────────────────────────────

do_dump() {
    local db="$1"
    local ts
    ts="$(timestamp)"
    local day_of_week
    day_of_week="$(date +%u)"  # 1=Mon, 7=Sun

    local subdir
    if [ "$day_of_week" -eq 7 ]; then
        subdir="weekly"
    else
        subdir="daily"
    fi

    local dump_dir="$BACKUP_DIR/$subdir/$db"
    mkdir -p "$dump_dir"
    local dump_file="$dump_dir/${db}_${ts}.dump"
    local dump_log="$dump_dir/${db}_${ts}.log"

    info "Dumping database: $db → $dump_file"

    if [ "$DRY_RUN" = "true" ]; then
        info "[DRY-RUN] Would run: pg_dump -h $PG_HOST -p $PG_PORT -U $PG_USER -d $db --format=custom --compress=9 --file=$dump_file"
        return 0
    fi

    if pg_dump_cmd "$db" "$dump_file" > "$dump_log" 2>&1; then
        local size
        size="$(du -h "$dump_file" | cut -f1)"
        ok "Dump succeeded: $db ($size)"
        return 0
    else
        err "Dump failed for $db — see $dump_log"
        return 1
    fi
}

do_restore() {
    local db="$1"
    local latest

    # Find the most recent dump for this database
    latest=$(find "$BACKUP_DIR" -name "${db}_*.dump" -type f 2>/dev/null | sort | tail -1)

    if [ -z "$latest" ]; then
        err "No backup found for database: $db"
        return 1
    fi

    info "Restoring database: $db ← $latest"
    if [ "$DRY_RUN" = "true" ]; then
        info "[DRY-RUN] Would restore: $latest into $db"
        return 0
    fi

    local restore_log="${latest%.dump}_restore.log"
    if pg_restore_cmd "$db" "$latest" > "$restore_log" 2>&1; then
        ok "Restore succeeded: $db"
        return 0
    else
        err "Restore failed for $db — see $restore_log"
        return 1
    fi
}

do_pitr_config() {
    cat << 'PITR_CONFIG'
# =============================================================================
# WAL Archiving for Point-in-Time Recovery (PITR)
# =============================================================================
# Add these settings to your postgresql.conf (or Docker entrypoint).
#
# For Docker, mount the config at:
#   /etc/postgresql/postgresql.conf  (Debian-based PG images)
# or set via environment variable:
#   POSTGRES_CONFIG_FILE=/etc/postgresql/postgresql.conf
# =============================================================================

wal_level = replica               # Minimum level for archiving
archive_mode = on                 # Enable WAL archiving
archive_command = 'pg_check_ready && cp %p /var/lib/postgresql/archive/%f'
archive_timeout = 60              # Force archive every 60 seconds

# Restore (recovery) — when recovering from a base backup:
# restore_command = 'cp /var/lib/postgresql/archive/%f %p'
# recovery_target_time = '2025-06-01 14:30:00 IST'  # Uncomment to PITR to a specific time

# Retention: keep enough WAL for full recovery + 7 days of PITR window
max_wal_size = 4GB
min_wal_size = 1GB
wal_keep_size = 2GB              # Keep 2GB of WAL for standby/PITR

# Performance tuning for archiving
archive_cleanup_command = 'pg_archivecleanup /var/lib/postgresql/archive %r 2>/dev/null; find /var/lib/postgresql/archive -name "*.partial" -delete'
PITR_CONFIG
}

do_prune() {
    local subdir="$1" retention="$2"

    info "Pruning backups older than $retention days ($subdir)..."
    if [ "$DRY_RUN" = "true" ]; then
        info "[DRY-RUN] Would delete backups in $BACKUP_DIR/$subdir older than $retention days"
        return 0
    fi

    find "$BACKUP_DIR/$subdir" -name "*.dump" -type f -mtime "+$retention" -delete 2>/dev/null || true
    find "$BACKUP_DIR/$subdir" -name "*.log" -type f -mtime "+$retention" -delete 2>/dev/null || true

    # Remove empty directories
    find "$BACKUP_DIR/$subdir" -type d -empty -delete 2>/dev/null || true
    ok "Pruned $subdir backups older than $retention days"
}

do_upload() {
    if [ -z "${BACKUP_S3_PATH:-}" ] && [ -z "${RCLONE_REMOTE:-}" ]; then
        warn "No remote backup target configured (set BACKUP_S3_PATH or RCLONE_REMOTE)"
        return 0
    fi

    info "Uploading backups to remote..."
    if [ "$DRY_RUN" = "true" ]; then
        info "[DRY-RUN] Would upload $BACKUP_DIR to remote"
        return 0
    fi

    if [ -n "${BACKUP_S3_PATH:-}" ]; then
        if command -v aws &>/dev/null; then
            aws s3 sync "$BACKUP_DIR" "$BACKUP_S3_PATH" --quiet
            ok "Uploaded to S3: $BACKUP_S3_PATH"
        elif command -v rclone &>/dev/null; then
            rclone sync "$BACKUP_DIR" "${BACKUP_S3_PATH#s3://}" --progress
            ok "Uploaded via rclone to: $BACKUP_S3_PATH"
        else
            warn "Neither aws CLI nor rclone found — skipping remote upload"
        fi
    fi

    if [ -n "${RCLONE_REMOTE:-}" ]; then
        if command -v rclone &>/dev/null; then
            rclone sync "$BACKUP_DIR" "$RCLONE_REMOTE" --progress
            ok "Uploaded via rclone to: $RCLONE_REMOTE"
        else
            warn "rclone not found — skipping remote upload to $RCLONE_REMOTE"
        fi
    fi
}

do_list() {
    info "Backups in $BACKUP_DIR:"
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "*.dump" -type f | sort -r | while read -r f; do
            size=$(du -h "$f" | cut -f1)
            echo "  $size  $f"
        done
    else
        warn "No backups directory found at $BACKUP_DIR"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
    local db_filter=""
    local action="dump"  # dump | restore | list | pitr-config

    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --db=*)
                db_filter="${arg#*=}"
                ;;
            --dry-run)
                DRY_RUN=true
                ;;
            --restore=*)
                action="restore"
                db_filter="${arg#*=}"
                ;;
            --list)
                action="list"
                ;;
            --show-pitr-config)
                action="pitr-config"
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --db=NAME         Operate on a single database (default: all)"
                echo "  --dry-run         Show what would be done without doing it"
                echo "  --restore=NAME    Restore the latest backup for database NAME"
                echo "  --list            List available backups"
                echo "  --show-pitr-config  Print PITR/WAL archiving config snippet"
                echo "  --help, -h        Show this help"
                exit 0
                ;;
            *)
                err "Unknown argument: $arg"
                exit 1
                ;;
        esac
    done

    # Handle special actions
    case "$action" in
        list)
            do_list
            exit 0
            ;;
        pitr-config)
            do_pitr_config
            exit 0
            ;;
    esac

    # Determine which databases to operate on
    if [ -n "$db_filter" ]; then
        dbs_to_process=("$db_filter")
    else
        dbs_to_process=("${DATABASES[@]}")
    fi

    case "$action" in
        dump)
            info "Starting backup for ${#dbs_to_process[@]} database(s)..."
            info "Backup directory: $BACKUP_DIR"
            echo ""

            local exit_code=0
            for db in "${dbs_to_process[@]}"; do
                do_dump "$db" || exit_code=$?
            done

            echo ""
            if [ "$exit_code" -eq 0 ]; then
                ok "All dumps completed successfully"
            else
                err "Some dumps failed (exit code: $exit_code)"
            fi

            # Prune old backups
            do_prune "daily" "$RETENTION_DAILY"
            do_prune "weekly" "$RETENTION_WEEKLY"

            # Upload to remote
            do_upload

            exit "$exit_code"
            ;;
        restore)
            if [ -z "$db_filter" ]; then
                err "Restore requires --db=NAME"
                exit 1
            fi
            do_restore "$db_filter"
            exit $?
            ;;
    esac
}

main "$@"
