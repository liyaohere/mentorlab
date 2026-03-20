#!/bin/bash
# Database backup script for MentorLab
# Usage: ./scripts/backup_db.sh
# Produces: backups/mentorlab_YYYYMMDD_HHMMSS.sql.gz
#
# For automated daily backups, add to crontab:
#   0 2 * * * cd /path/to/mentorlab && ./scripts/backup_db.sh

set -euo pipefail

BACKUP_DIR="$(dirname "$0")/../backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="mentorlab_${TIMESTAMP}.sql.gz"

# Source .env for DATABASE_URL if available
ENV_FILE="$(dirname "$0")/../backend/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep DATABASE_URL | xargs)
fi

# Default connection params
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-mentorlab}"
DB_USER="${PGUSER:-postgres}"

echo "Backing up database ${DB_NAME}..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "${BACKUP_DIR}/${FILENAME}"

FILESIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "Backup saved: ${BACKUP_DIR}/${FILENAME} (${FILESIZE})"

# Keep only last 30 backups
cd "$BACKUP_DIR"
ls -t mentorlab_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm --
echo "Cleanup done. $(ls mentorlab_*.sql.gz 2>/dev/null | wc -l | tr -d ' ') backups retained."
