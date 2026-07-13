#!/usr/bin/env bash
# 启动 geoflow-admin 前端（源码目录直跑，Next.js HMR 热更新）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADMIN_DIR="${GEOFLOW_ADMIN_SRC:-${ROOT}/apps/geoflow-admin}"
PORT="${ADMIN_PORT:-13001}"
API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:${API_PORT:-18081}}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if [ ! -d "${ADMIN_DIR}" ]; then
  log "ERROR: Admin 源码目录不存在: ${ADMIN_DIR}"
  exit 1
fi

cd "${ADMIN_DIR}"

if [ ! -d "node_modules/next" ]; then
  log "首次安装依赖 → ${ADMIN_DIR}"
  NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin npm install
fi

# 外置盘/网络盘默认轮询监听，否则保存后 HMR 可能不触发
export WATCHPACK_POLLING="${WATCHPACK_POLLING:-true}"
export CHOKIDAR_USEPOLLING="${CHOKIDAR_USEPOLLING:-true}"

log "Admin 源码目录: ${ADMIN_DIR}"
log "启动 Admin (HMR) → http://127.0.0.1:${PORT}/login"
log "API 代理目标: ${API_URL} (浏览器请求走 /api/* 同源代理)"

admin_alive() {
  curl -sf "http://127.0.0.1:${PORT}/login" >/dev/null 2>&1
}

watchdog_alive() {
  [ -f /tmp/geoflow-v3-admin.pid ] \
    && ps -p "$(cat /tmp/geoflow-v3-admin.pid)" >/dev/null 2>&1 \
    && ps -p "$(cat /tmp/geoflow-v3-admin.pid)" -o args= 2>/dev/null | grep -q run-admin-watchdog
}

if [ "${GEOFLOW_ADMIN_DAEMON:-0}" = "1" ]; then
  if watchdog_alive && admin_alive; then
    log "Admin watchdog 已在运行 (PID $(cat /tmp/geoflow-v3-admin.pid))"
    exit 0
  fi
  pkill -f "next dev.*--port ${PORT}" 2>/dev/null || true
  pkill -f "run-admin-watchdog.sh" 2>/dev/null || true
  sleep 1
  "${ROOT}/scripts/daemonize.sh" "${ROOT}/scripts/run-admin-watchdog.sh" /tmp/geoflow-v3-admin.log /tmp/geoflow-v3-admin.pid
  WATCHDOG_PID=$(cat /tmp/geoflow-v3-admin.pid)
  sleep 8
  if ! admin_alive; then
    log "ERROR: Admin 启动失败，见 /tmp/geoflow-v3-admin.log"
    tail -20 /tmp/geoflow-v3-admin.log
    exit 1
  fi
  log "Admin watchdog PID=$(cat /tmp/geoflow-v3-admin.pid) 健康检查通过"
else
  exec env NEXT_PUBLIC_API_URL="${API_URL}" \
    NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin \
    npm run dev -- --port "${PORT}" --hostname 127.0.0.1 --webpack
fi
