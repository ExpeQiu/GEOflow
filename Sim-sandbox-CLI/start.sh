#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PORT="${SIMSB_PORT:-8765}"
HOST="${SIMSB_HOST:-127.0.0.1}"
PID_FILE="$ROOT/.simsb-web.pid"
LOG_FILE="$ROOT/.simsb-web.log"

log() { echo "[start] $*"; }

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    log "已在运行 pid=$old_pid  http://${HOST}:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  log "创建 venv..."
  python3 -m venv "$ROOT/.venv"
fi

log "安装依赖 [web]..."
"$ROOT/.venv/bin/pip" install -q -e ".[web,dev]"

log "启动 Web http://${HOST}:${PORT}"
: >"$LOG_FILE"
(
  cd "$ROOT"
  exec "$ROOT/.venv/bin/python" -m uvicorn simsb.web.app:app \
    --host "$HOST" --port "$PORT"
) >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
disown "$(cat "$PID_FILE")" 2>/dev/null || true

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf "http://${HOST}:${PORT}/api/health" >/dev/null 2>&1; then
    log "就绪 pid=$(cat "$PID_FILE") 日志 $LOG_FILE"
    log "打开 http://${HOST}:${PORT}"
    exit 0
  fi
  sleep 0.4
done

log "启动失败，见 $LOG_FILE"
tail -n 40 "$LOG_FILE" || true
exit 1
