#!/bin/sh
set -e

BACKUP_ROOT="/backup"
OUTPUT_PATH="$BACKUP_ROOT/output"
MEDIA_PATH="$BACKUP_ROOT/media"
DATA_FILE="$BACKUP_ROOT/data.json"

mkdir -p "$OUTPUT_PATH"
mkdir -p "$MEDIA_PATH"

# Ensure data.json exists and is valid JSON
if [ ! -f "$DATA_FILE" ] || [ ! -s "$DATA_FILE" ]; then
  echo "{}" > "$DATA_FILE"
fi

exec python /app/export.py "$@"
