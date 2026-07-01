#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  log "已从 .env.example 创建 .env"
fi

log "启动 GEOFlow v3 Docker Compose..."
docker compose up -d postgres redis
sleep 3
docker compose up -d --build api worker scheduler flower geoflow-admin

log "执行数据库迁移..."
docker compose exec -T api alembic upgrade head || true
docker compose exec -T api python scripts/seed.py || true

API_PORT="${API_PORT:-18081}"
ADMIN_PORT="${ADMIN_PORT:-13001}"
log "完成。API: http://127.0.0.1:${API_PORT}/health"
log "Admin: http://127.0.0.1:${ADMIN_PORT}/login"
log "Flower: http://127.0.0.1:15555"
