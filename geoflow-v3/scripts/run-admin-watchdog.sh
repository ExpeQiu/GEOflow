#!/usr/bin/env bash
# Admin 守护：进程退出后自动重启
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${ADMIN_PORT:-13001}"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Admin 启动..." >> /tmp/geoflow-v3-admin.log
  GEOFLOW_ADMIN_DAEMON=0 "${ROOT}/scripts/start-admin.sh" >> /tmp/geoflow-v3-admin.log 2>&1 || true
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Admin 退出，2s 后重启" >> /tmp/geoflow-v3-admin.log
  pkill -f "next dev.*--port ${PORT}" 2>/dev/null || true
  sleep 2
done
