#!/usr/bin/env bash
# 启动 geoflow-admin 前端（源码目录直跑，Next.js HMR）
# 默认：前台；GEOFLOW_ADMIN_DAEMON=1 或传 --daemon 则后台守护
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"

ADMIN_DIR="${GEOFLOW_ADMIN_SRC:-${ROOT}/apps/geoflow-admin}"
PORT="${ADMIN_PORT}"
API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:${API_PORT}}"
DAEMON="${GEOFLOW_ADMIN_DAEMON:-0}"
for arg in "$@"; do
  case "${arg}" in
    --daemon|-d) DAEMON=1 ;;
    --foreground|-f) DAEMON=0 ;;
  esac
done

log "===== start-admin 开始 (daemon=${DAEMON}) ====="

if [ ! -d "${ADMIN_DIR}" ]; then
  err "Admin 源码目录不存在: ${ADMIN_DIR}"
  exit 1
fi

require_cmd npm curl || exit 1
cd "${ADMIN_DIR}"

if [ ! -d "node_modules/next" ]; then
  log "首次安装依赖 → ${ADMIN_DIR}"
  NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin npm install
fi

# 外置盘默认轮询，保证 HMR
export WATCHPACK_POLLING="${WATCHPACK_POLLING:-true}"
export CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-true}"
export NEXT_PUBLIC_API_URL="${API_URL}"

log "Admin 源码: ${ADMIN_DIR}"
log "Admin URL → http://127.0.0.1:${PORT}/login"
log "API 代理 → ${API_URL}"

if [ "${DAEMON}" = "1" ]; then
  if wait_http_ok "http://127.0.0.1:${PORT}/login" 2 \
    && watchdog_alive "${GEOFLOW_ADMIN_PID}" "run-admin-watchdog.sh"; then
    log "Admin 已在运行 (PID $(tr -d '[:space:]' <"${GEOFLOW_ADMIN_PID}"))"
    exit 0
  fi
  pkill -f "next dev.*--port ${PORT}" 2>/dev/null || true
  ensure_daemon \
    "Admin" \
    "run-admin-watchdog.sh" \
    "${ROOT}/scripts/run-admin-watchdog.sh" \
    "${GEOFLOW_ADMIN_LOG}" \
    "${GEOFLOW_ADMIN_PID}" \
    "http://127.0.0.1:${PORT}/login" \
    "" \
    60
  log "===== start-admin 完成 ====="
  exit 0
fi

exec env NEXT_PUBLIC_API_URL="${API_URL}" \
  NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin \
  npm run dev -- --port "${PORT}" --hostname 127.0.0.1 --webpack
