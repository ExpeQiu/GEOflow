#!/usr/bin/env bash
# 开发环境常驻启动（API watchdog + Admin 源码 HMR，Ctrl+C 停止）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADMIN_DIR="${GEOFLOW_ADMIN_SRC:-${ROOT}/apps/geoflow-admin}"
ADMIN_PORT="${ADMIN_PORT:-13001}"
API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:${API_PORT:-18081}}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

"${ROOT}/scripts/start-local.sh"

if [ ! -d "${ADMIN_DIR}/node_modules/next" ]; then
  log "首次安装 Admin 依赖 → ${ADMIN_DIR}"
  (cd "${ADMIN_DIR}" && NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin npm install)
fi

export WATCHPACK_POLLING="${WATCHPACK_POLLING:-true}"
export CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-true}"

start_admin() {
  pkill -f "next dev.*--port ${ADMIN_PORT}" 2>/dev/null || true
  sleep 1
  cd "${ADMIN_DIR}"
  env NEXT_PUBLIC_API_URL="${API_URL}" \
    NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin \
    npm run dev -- --port "${ADMIN_PORT}" --hostname 127.0.0.1 --webpack \
    >> /tmp/geoflow-v3-admin.log 2>&1 &
  echo $! > /tmp/geoflow-v3-admin.pid
  cd "${ROOT}"
}

if ! curl -sf "http://127.0.0.1:${ADMIN_PORT}/login" >/dev/null 2>&1; then
  start_admin
  sleep 6
fi

"${ROOT}/scripts/verify-services.sh"

log "服务已就绪"
log "Admin (HMR): http://127.0.0.1:${ADMIN_PORT}/login  账号 admin / password"
log "Admin 源码: ${ADMIN_DIR}"
log "API:   http://127.0.0.1:${API_PORT:-18081}/health"
log "Ctrl+C 停止服务"

cleanup() {
  log "停止 Admin / API watchdog..."
  kill "$(cat /tmp/geoflow-v3-admin.pid 2>/dev/null)" 2>/dev/null || true
  pkill -f "run-api-watchdog.sh" 2>/dev/null || true
  pkill -f "uvicorn app.main:app.*${API_PORT:-18081}" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

ADMIN_PID="$(cat /tmp/geoflow-v3-admin.pid 2>/dev/null || true)"
if [ -n "${ADMIN_PID}" ] && kill -0 "${ADMIN_PID}" 2>/dev/null; then
  wait "${ADMIN_PID}" || true
else
  while curl -sf "http://127.0.0.1:${API_PORT:-18081}/health" >/dev/null 2>&1 \
     || curl -sf "http://127.0.0.1:${ADMIN_PORT}/login" >/dev/null 2>&1; do
    sleep 10
  done
fi
