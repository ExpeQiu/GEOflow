#!/usr/bin/env bash
# 本地 Celery Worker 常驻启动
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if pgrep -f "celery -A app.workers.celery_app worker" >/dev/null 2>&1; then
  log "Worker 已在运行 PID=$(pgrep -f 'celery -A app.workers.celery_app worker' | head -1)"
  exit 0
fi

pkill -f "celery -A app.workers.celery_app worker" 2>/dev/null || true
sleep 1
chmod +x "${ROOT}/scripts/run-worker.sh" "${ROOT}/scripts/run-worker-watchdog.sh"
"${ROOT}/scripts/daemonize.sh" "${ROOT}/scripts/run-worker-watchdog.sh" /tmp/geoflow-v3-worker.log /tmp/geoflow-v3-worker.pid

for _ in 1 2 3 4 5; do
  if pgrep -f "celery -A app.workers.celery_app worker" >/dev/null 2>&1; then
    log "Worker 已启动 PID=$(cat /tmp/geoflow-v3-worker.pid 2>/dev/null || pgrep -f 'celery -A app.workers.celery_app worker' | head -1)"
    log "日志: /tmp/geoflow-v3-worker.log"
    exit 0
  fi
  sleep 1
done

log "ERROR: Worker 启动失败，见 /tmp/geoflow-v3-worker.log"
tail -20 /tmp/geoflow-v3-worker.log
exit 1
