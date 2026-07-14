#!/usr/bin/env bash
# 停止本地进程；默认只 stop Postgres（保留容器与数据卷）
# 用法:
#   ./scripts/stop.sh           # 停进程 + stop 容器
#   ./scripts/stop.sh --purge   # 额外 rm 容器（仍保留 volume，可手动恢复）
#   ./scripts/stop.sh --wipe-db # 危险：rm 容器并删除命名数据卷
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"

PURGE=0
WIPE_DB=0
for arg in "$@"; do
  case "${arg}" in
    --purge) PURGE=1 ;;
    --wipe-db) WIPE_DB=1; PURGE=1 ;;
  esac
done

log "===== stop 开始 ====="
log "停止 Admin / API / Worker 本地进程..."
pkill -f "run-admin-watchdog.sh" 2>/dev/null || true
pkill -f "next dev.*--port ${ADMIN_PORT}" 2>/dev/null || true
pkill -f "run-api-watchdog.sh" 2>/dev/null || true
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}" 2>/dev/null || true
pkill -f "run-worker-watchdog.sh" 2>/dev/null || true
pkill -f "celery -A app.workers.celery_app worker" 2>/dev/null || true
rm -f "${GEOFLOW_ADMIN_PID}" "${GEOFLOW_API_PID}" "${GEOFLOW_WORKER_PID}"

if docker ps --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  log "停止 PostgreSQL 容器（保留数据卷）: ${PG_NAME}"
  docker stop "${PG_NAME}" >/dev/null
elif docker ps -a --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  log "PostgreSQL 容器已是停止状态: ${PG_NAME}"
else
  log "未发现 PostgreSQL 容器 ${PG_NAME}"
fi

if [[ "${PURGE}" == "1" ]]; then
  log "purge: 移除容器 ${PG_NAME}（volume 默认保留）"
  docker rm -f "${PG_NAME}" 2>/dev/null || true
fi

if [[ "${WIPE_DB}" == "1" ]]; then
  err "wipe-db: 删除命名卷 ${PG_VOL}（不可恢复）"
  docker volume rm "${PG_VOL}" 2>/dev/null || true
  log "注意: 历史匿名卷 ${PG_LEGACY_VOL:0:12}... 未自动删除；确认无用后再 docker volume rm"
fi

cd "$ROOT"
if docker compose ps -q 2>/dev/null | grep -q .; then
  log "docker compose down（不删 volume）..."
  docker compose down 2>/dev/null || true
fi

log "GEOFlow v3 已停止"
log "===== stop 完成 ====="
