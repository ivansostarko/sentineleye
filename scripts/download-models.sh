#!/usr/bin/env bash
# scripts/download-models.sh — fetch YOLO weights into the ai-models volume.
set -euo pipefail

MODELS_DIR="${1:-./.docker-data/ai-models}"
mkdir -p "$MODELS_DIR"

declare -a MODELS=(
  "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
  "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt"
)

for url in "${MODELS[@]}"; do
  name="$(basename "$url")"
  if [[ -f "$MODELS_DIR/$name" ]]; then
    echo "✓ $name (cached)"
    continue
  fi
  echo "→ downloading $name"
  curl -L --fail -o "$MODELS_DIR/$name" "$url"
done

echo "Done. Set YOLO_MODEL=yolov8s.pt in .env to use the bigger model."
