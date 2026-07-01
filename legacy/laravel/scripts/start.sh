#!/usr/bin/env bash
# GEOworkflow Docker 启动（GEO 策略为内置模块；仅当 START_GEO_OS=true 时才联动外部 GEO 仓库）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GEO_ROOT="${GEO_OS_ROOT:-/Volumes/Lexar/git/02 POC/GEO}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

cd "$ROOT"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  log "已从 .env.example 创建 .env，请按需修改 GEO_EVAL_*"
fi

if command -v docker >/dev/null 2>&1 && [ -f docker-compose.yml ]; then
  log "启动 GEOworkflow Docker Compose..."
  docker compose up -d postgres redis
  docker compose run --rm init 2>/dev/null || docker compose up -d init
  log "构建并启动 Content Agent 侧车..."
  docker compose up -d --build content-agent
  docker compose up -d app queue scheduler reverb
  docker compose exec -T app php artisan migrate --force 2>/dev/null || true
  docker compose exec -T app php artisan config:clear 2>/dev/null || true
else
  log "未检测到 docker，回退 php artisan serve"
  php artisan serve --host=127.0.0.1 --port="${APP_PORT:-8080}" &
fi

if [ "${START_GEO_OS:-false}" = "true" ] && [ -f "$GEO_ROOT/start.sh" ]; then
  log "启动 GEO-OS（宿主机/独立 compose）..."
  (cd "$GEO_ROOT" && ./start.sh docker) || log "WARN: GEO-OS 启动失败"
fi

APP_PORT="${APP_PORT:-18080}"
log "完成。后台: http://127.0.0.1:${APP_PORT}/geo_admin"
log "评估排障: http://127.0.0.1:${APP_PORT}/geo_admin/geo-eval/diagnostics"
