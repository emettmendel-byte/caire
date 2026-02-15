#!/usr/bin/env bash
# Backup SQLite database to a timestamped file.
# Usage: ./scripts/backup_db.sh [destination_dir]
# Default destination: ./backups (created if missing)
# CAIRE_DB_PATH env overrides database path (default: ./caire.db).

set -e
DB_PATH="${CAIRE_DB_PATH:-./caire.db}"
DEST="${1:-./backups}"
mkdir -p "$DEST"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$DEST/caire_db_$STAMP.db"
if [[ -f "$DB_PATH" ]]; then
  cp "$DB_PATH" "$BACKUP_FILE"
  echo "Backed up $DB_PATH to $BACKUP_FILE"
else
  echo "Database not found at $DB_PATH" >&2
  exit 1
fi
