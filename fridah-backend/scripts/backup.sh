#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/fridah"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="fridah_db_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "==> Backing up database to ${BACKUP_DIR}/${FILENAME}"
docker compose exec -T db pg_dump -U "${DB_USER:-fridah}" "${DB_NAME:-fridah}" | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "==> Removing backups older than 14 days"
find "$BACKUP_DIR" -name "fridah_db_*.sql.gz" -mtime +14 -delete

echo "==> Backup complete: ${FILENAME}"
