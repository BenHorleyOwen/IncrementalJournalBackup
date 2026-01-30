#!/bin/sh
set -e

# Expected paths passed via args
# Defaults are aligned with compose
OUTPUT_PATH="/output"
MEDIA_PATH="/media"
DATA_FILE="/data.json"

# Create directories if missing
mkdir -p "$OUTPUT_PATH"
mkdir -p "$MEDIA_PATH"

# Initialize data file if missing or empty
if [ ! -f "$DATA_FILE" ] || [ ! -s "$DATA_FILE" ]; then
  echo "{}" > "$DATA_FILE"
fi

# Hand off to the real command
exec "$@"
