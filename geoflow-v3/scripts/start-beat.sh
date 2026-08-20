#!/usr/bin/env bash
# 本地 Celery Beat 常驻启动
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if pgrep -f "celery -A app.workers.celery_app beat" >/dev/null 2>&1; then
  log "Beat 已在运行 PID=$(pgrep -f 'celery -A app.workers.celery_app beat' | head -1)"
  exit 0
fi

pkill -f "celery -A app.workers.celery_app beat" 2>/dev/null || true
sleep 1
chmod +x "${ROOT}/scripts/run-beat.sh" "${ROOT}/scripts/run-beat-watchdog.sh"
"${ROOT}/scripts/daemonize.sh" "${ROOT}/scripts/run-beat-watchdog.sh" /tmp/geoflow-v3-beat.log /tmp/geoflow-v3-beat.pid

for _ in 1 2 3 4 5; do
  if pgrep -f "celery -A app.workers.celery_app beat" >/dev/null 2>&1; then
    log "Beat 已启动 PID=$(cat /tmp/geoflow-v3-beat.pid 2>/dev/null || pgrep -f 'celery -A app.workers.celery_app beat' | head -1)"
    log "日志: /tmp/geoflow-v3-beat.log"
    exit 0
  fi
  sleep 1
done

log "ERROR: Beat 启动失败，见 /tmp/geoflow-v3-beat.log"
tail -20 /tmp/geoflow-v3-beat.log
exit 1
