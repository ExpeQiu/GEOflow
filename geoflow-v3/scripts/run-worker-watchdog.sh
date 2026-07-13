#!/usr/bin/env bash
# Worker 守护：进程退出后自动重启
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Worker 启动..." >> /tmp/geoflow-v3-worker.log
  "${ROOT}/scripts/run-worker.sh" >> /tmp/geoflow-v3-worker.log 2>&1 || true
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Worker 退出，2s 后重启" >> /tmp/geoflow-v3-worker.log
  sleep 2
done
