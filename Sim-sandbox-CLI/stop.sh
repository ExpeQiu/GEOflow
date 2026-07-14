#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/.simsb-web.pid"

log() { echo "[stop] $*"; }

if [[ ! -f "$PID_FILE" ]]; then
  log "无 PID 文件，尝试按端口清理"
else
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 0.3
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    log "已停止 pid=$pid"
  else
    log "进程不存在 pid=${pid:-?}"
  fi
  rm -f "$PID_FILE"
fi

PORT="${SIMSB_PORT:-8765}"
if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    log "已释放端口 $PORT"
  fi
fi
