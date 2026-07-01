#!/usr/bin/env bash
# API 守护：进程退出后自动重启
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] API 启动..." >> /tmp/geoflow-v3-api.log
  "${ROOT}/scripts/run-api.sh" >> /tmp/geoflow-v3-api.log 2>&1 || true
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] API 退出，2s 后重启" >> /tmp/geoflow-v3-api.log
  sleep 2
done
