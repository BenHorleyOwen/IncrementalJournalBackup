#!/bin/sh
set -e

OUTPUT_PATH="/output"
MEDIA_PATH="/media"
DATA_FILE="data.json"

mkdir -p "$OUTPUT_PATH"
mkdir -p "$MEDIA_PATH"

if [ ! -f "$DATA_FILE" ] || [ ! -s "$DATA_FILE" ]; then
  echo "{}" > "$DATA_FILE"
fi

# Always run the app, passing through args
exec python /app/export.py "$@"

