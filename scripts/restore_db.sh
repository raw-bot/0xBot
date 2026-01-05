#!/bin/bash
# 0xBot PostgreSQL Restore Script
# Usage: ./restore_db.sh backup_20260105_123456.sql.gz

BACKUP_DIR="/Users/cube/Documents/00-code/0xBot/backups"
CONTAINER_NAME="trading_agent_postgres"
DB_NAME="trading_agent"
DB_USER="postgres"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$BACKUP_DIR/$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will REPLACE all data in the database!"
echo "Restore from: $1"
read -p "Are you sure? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Restoring..."

    # Drop and recreate database
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" 2>/dev/null
    docker exec "$CONTAINER_NAME" dropdb -U "$DB_USER" "$DB_NAME" 2>/dev/null
    docker exec "$CONTAINER_NAME" createdb -U "$DB_USER" "$DB_NAME"

    # Restore
    gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME"

    if [ $? -eq 0 ]; then
        echo "✅ Restore successful!"
    else
        echo "❌ Restore failed!"
        exit 1
    fi
else
    echo "Cancelled."
fi
