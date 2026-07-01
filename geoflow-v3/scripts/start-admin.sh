#!/usr/bin/env bash
# 启动 geoflow-admin 前端（外置盘 npm 慢/缓存问题时，复制到 /tmp 安装）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/apps/geoflow-admin"
DEV_DIR="${GEOFLOW_ADMIN_DEV_DIR:-/tmp/geoflow-admin-dev}"
PORT="${ADMIN_PORT:-13001}"
API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:${API_PORT:-18081}}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if [ ! -d "${DEV_DIR}/node_modules/next" ]; then
  log "首次安装：复制到 ${DEV_DIR} 并 npm install..."
  rm -rf "${DEV_DIR}"
  cp -R "${SRC}" "${DEV_DIR}"
  cd "${DEV_DIR}"
  NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin npm install
else
  log "同步源码到 ${DEV_DIR}..."
  rsync -a --delete \
    --exclude node_modules --exclude .next \
    "${SRC}/" "${DEV_DIR}/"
  cd "${DEV_DIR}"
fi

log "启动 Admin → http://127.0.0.1:${PORT}/login"
log "API 代理目标: ${API_URL} (浏览器请求走 /api/* 同源代理)"

if [ "${GEOFLOW_ADMIN_DAEMON:-0}" = "1" ]; then
  pkill -f "next dev.*--port ${PORT}" 2>/dev/null || true
  sleep 1
  nohup env NEXT_PUBLIC_API_URL="${API_URL}" \
    NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin \
    npm run dev -- --port "${PORT}" --hostname 127.0.0.1 \
    >> /tmp/geoflow-v3-admin.log 2>&1 </dev/null &
  echo $! > /tmp/geoflow-v3-admin.pid
  log "Admin 后台 PID=$(cat /tmp/geoflow-v3-admin.pid)"
else
  exec env NEXT_PUBLIC_API_URL="${API_URL}" \
    NPM_CONFIG_CACHE=/tmp/npm-cache-geoflow-admin \
    npm run dev -- --port "${PORT}" --hostname 127.0.0.1
fi
