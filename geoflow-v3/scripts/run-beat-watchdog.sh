#!/usr/bin/env bash
# Beat 守护：进程退出后自动重启
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Beat 启动..." >> /tmp/geoflow-v3-beat.log
  "${ROOT}/scripts/run-beat.sh" >> /tmp/geoflow-v3-beat.log 2>&1 || true
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Beat 退出，2s 后重启" >> /tmp/geoflow-v3-beat.log
  sleep 2
done
