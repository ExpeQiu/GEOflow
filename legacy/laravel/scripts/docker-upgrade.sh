#!/usr/bin/env bash
# 本地 Docker 升级：拉代码后重建镜像、迁移 GEO 评估表、重启队列
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if ! command -v docker >/dev/null 2>&1; then
  echo "docker 未安装" >&2
  exit 1
fi

log "重建镜像（如有 Dockerfile 变更）..."
docker compose build app

log "启动依赖与一次性 init（迁移 + seed）..."
docker compose up -d postgres redis
docker compose run --rm init

log "重启应用与队列..."
docker compose up -d app queue scheduler reverb

log "执行增量迁移（含 geo_eval 表）..."
docker compose exec -T app php artisan migrate --force

log "清理配置缓存..."
docker compose exec -T app php artisan config:clear

log "健康检查..."
curl -sf "http://127.0.0.1:${APP_PORT:-18080}/" >/dev/null && log "前台 OK" || log "WARN: 前台未响应，请检查 APP_PORT"

if docker compose exec -T app php artisan about >/dev/null 2>&1; then
  log "artisan OK"
fi

log "完成。后台: http://127.0.0.1:${APP_PORT:-18080}/geo_admin"
log "评估排障: http://127.0.0.1:${APP_PORT:-18080}/geo_admin/geo-eval/diagnostics"
