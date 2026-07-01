#!/usr/bin/env bash
# 一键启动 API + Admin 前端
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

"${ROOT}/scripts/start-local.sh"

if ! curl -sf "http://127.0.0.1:${ADMIN_PORT:-13001}/login" >/dev/null 2>&1; then
  GEOFLOW_ADMIN_DAEMON=1 "${ROOT}/scripts/start-admin.sh"
  sleep 6
fi

"${ROOT}/scripts/verify-services.sh"
log() { echo "[$(date '+%H:%M:%S')] $*"; }
log "访问 Admin: http://127.0.0.1:${ADMIN_PORT:-13001}/login  (admin / password)"
