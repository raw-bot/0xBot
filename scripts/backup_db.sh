#!/bin/bash
# 0xBot PostgreSQL Backup Script
# Runs daily and keeps 7 days of backups

BACKUP_DIR="/Users/cube/Documents/00-code/0xBot/backups"
CONTAINER_NAME="trading_agent_postgres"
DB_NAME="trading_agent"
DB_USER="postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DATE}.sql.gz"
KEEP_DAYS=7

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting backup at $(date)"

# Create compressed backup
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "✅ Backup successful: $BACKUP_FILE ($SIZE)"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Remove old backups (keep last KEEP_DAYS days)
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$KEEP_DAYS -delete
REMAINING=$(ls -1 "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | wc -l | tr -d ' ')
echo "📁 Keeping $REMAINING backup(s), removed backups older than $KEEP_DAYS days"

echo "✅ Backup complete!"
