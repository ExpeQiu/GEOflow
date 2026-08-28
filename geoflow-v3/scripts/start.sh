#!/usr/bin/env bash
# Docker Compose。默认全量；infra 只起 Postgres+Redis（供 Techstore/GEOweb 单独部署）
#   ./scripts/start.sh
#   ./scripts/start.sh infra
#   GEOFLOW_PULL=always ./scripts/start.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"
cd "$ROOT"

MODE="${1:-all}"
if [[ "${MODE}" != "all" && "${MODE}" != "infra" ]]; then
  err "用法: $0 [all|infra]"
  exit 2
fi

PULL_POLICY="${GEOFLOW_PULL:-never}"

log "===== start (compose) 开始 mode=${MODE} pull=${PULL_POLICY} ====="

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  log "已从 .env.example 创建 .env"
fi

require_cmd docker || exit 1

need_images=(pgvector/pgvector:pg16 redis:7-alpine)
missing=0
for img in "${need_images[@]}"; do
  if ! docker image inspect "${img}" >/dev/null 2>&1; then
    err "缺少本地镜像: ${img}"
    missing=1
  fi
done
if [[ "${missing}" == "1" && "${PULL_POLICY}" == "never" ]]; then
  err "本地镜像不全且 pull=never。可选："
  err "  1) 改用本地模式: ./scripts/start-all.sh"
  err "  2) 允许拉取: GEOFLOW_PULL=missing ./scripts/start.sh"
  exit 1
fi

log "启动基础设施 postgres + redis..."
docker compose up -d --pull "${PULL_POLICY}" postgres redis

i=0
until docker compose exec -T postgres pg_isready -U geo_user -d geo_flow >/dev/null 2>&1; do
  i=$((i + 1))
  if (( i > 40 )); then
    err "postgres 未就绪"
    docker compose logs --tail 40 postgres || true
    exit 1
  fi
  sleep 1
done
log "postgres ready"
"${ROOT}/scripts/ensure-shared-databases.sh"

if [[ "${MODE}" == "infra" ]]; then
  log "infra 完成。Postgres :${PG_PORT}  geo_flow + gweb_db  Redis :16380"
  log "===== start (compose) 完成 ====="
  exit 0
fi

log "构建并启动 api/worker/scheduler/flower/admin..."
docker compose up -d --build --pull "${PULL_POLICY}" api worker scheduler flower geoflow-admin

log "执行数据库迁移..."
if ! docker compose exec -T api alembic upgrade head; then
  err "alembic upgrade head 失败"
  exit 1
fi
if ! docker compose exec -T api python scripts/seed.py; then
  err "seed.py 失败"
  exit 1
fi

if ! wait_http_ok "http://127.0.0.1:${API_PORT}/health" 40 "ok"; then
  err "API 健康检查失败"
  docker compose logs --tail 40 api || true
  exit 1
fi

log "完成。API: http://127.0.0.1:${API_PORT}/health"
log "Admin: http://127.0.0.1:${ADMIN_PORT}/login"
log "Flower: http://127.0.0.1:15555"
log "===== start (compose) 完成 ====="
