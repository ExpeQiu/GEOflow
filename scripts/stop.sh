#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GEO_ROOT="${GEO_OS_ROOT:-/Volumes/Lexar/git/02 POC/GEO}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

cd "$ROOT"

if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
  log "停止 GEOworkflow Docker Compose..."
  docker compose down
else
  pkill -f "artisan serve" 2>/dev/null || true
fi

if [ -f "$GEO_ROOT/stop.sh" ]; then
  (cd "$GEO_ROOT" && ./stop.sh docker) 2>/dev/null || true
fi

log "已停止"
