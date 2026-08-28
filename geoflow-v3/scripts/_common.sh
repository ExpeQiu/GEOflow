#!/usr/bin/env bash
# GEOFlow v3 scripts 公共函数（被 source，勿直接执行）
# shellcheck disable=SC2034

: "${GEOFLOW_SCRIPTS_ROOT:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${GEOFLOW_ROOT:=$(cd "${GEOFLOW_SCRIPTS_ROOT}/.." && pwd)}"

: "${API_PORT:=18081}"
: "${ADMIN_PORT:=13001}"
: "${PG_PORT:=15433}"
: "${PG_NAME:=geoflow-v3-postgres-local}"
: "${PG_VOL:=geoflow-v3-postgres-local-data}"
# 历史匿名卷（start-local 曾 rm 容器后遗留）；仅在命名卷不存在时兜底复用
: "${PG_LEGACY_VOL:=31e2b35f17bb3a26a045332719ccc705d835f4f0600552feddd35edf479092a4}"

: "${GEOFLOW_API_PID:=/tmp/geoflow-v3-api.pid}"
: "${GEOFLOW_ADMIN_PID:=/tmp/geoflow-v3-admin.pid}"
: "${GEOFLOW_WORKER_PID:=/tmp/geoflow-v3-worker.pid}"
: "${GEOFLOW_BEAT_PID:=/tmp/geoflow-v3-beat.pid}"
: "${GEOFLOW_API_LOG:=/tmp/geoflow-v3-api.log}"
: "${GEOFLOW_ADMIN_LOG:=/tmp/geoflow-v3-admin.log}"
: "${GEOFLOW_WORKER_LOG:=/tmp/geoflow-v3-worker.log}"
: "${GEOFLOW_BEAT_LOG:=/tmp/geoflow-v3-beat.log}"
: "${GEOFLOW_START_LOG:=/tmp/geoflow-v3-start.log}"

log() {
  local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "${line}"
  if [[ -n "${GEOFLOW_START_LOG:-}" ]]; then
    echo "${line}" >>"${GEOFLOW_START_LOG}" 2>/dev/null || true
  fi
}

err() { log "ERROR: $*"; }

require_cmd() {
  local c
  for c in "$@"; do
    if ! command -v "${c}" >/dev/null 2>&1; then
      err "缺少命令: ${c}"
      return 1
    fi
  done
}

pid_alive() {
  local f="$1"
  [[ -f "${f}" ]] || return 1
  local pid
  pid="$(tr -d '[:space:]' <"${f}")"
  [[ -n "${pid}" ]] || return 1
  kill -0 "${pid}" 2>/dev/null
}

watchdog_alive() {
  local f="$1"
  local needle="$2"
  pid_alive "${f}" || return 1
  ps -p "$(tr -d '[:space:]' <"${f}")" -o args= 2>/dev/null | grep -q "${needle}"
}

wait_http_ok() {
  # usage: wait_http_ok URL [timeout_sec] [grep_pattern]
  local url="$1"
  local timeout="${2:-30}"
  local pattern="${3:-}"
  local i=0
  while (( i < timeout )); do
    if [[ -n "${pattern}" ]]; then
      if curl -sf --max-time 2 "${url}" 2>/dev/null | grep -q "${pattern}"; then
        return 0
      fi
    else
      if curl -sf --max-time 2 -o /dev/null "${url}" 2>/dev/null; then
        return 0
      fi
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

wait_pg_ready() {
  local name="${1:-${PG_NAME}}"
  local timeout="${2:-30}"
  local i=0
  while (( i < timeout )); do
    if docker exec "${name}" pg_isready -U geo_user -d geo_flow >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

redis_ok() {
  if command -v redis-cli >/dev/null 2>&1; then
    redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null | grep -q PONG
    return $?
  fi
  # 无 redis-cli 时仅探测端口
  (echo >/dev/tcp/127.0.0.1/6379) >/dev/null 2>&1
}

volume_has_pgdata() {
  local vol="$1"
  docker volume inspect "${vol}" >/dev/null 2>&1 || return 1
  # 探测卷内是否已有 PGDATA（存在 PG_VERSION）
  local out
  out="$(docker run --rm -v "${vol}:/data:ro" postgres:16-alpine \
    sh -c 'test -f /data/PG_VERSION && cat /data/PG_VERSION' 2>/dev/null || true)"
  [[ -n "${out}" ]]
}

resolve_pg_volume() {
  # 输出最终应挂载的卷名
  if volume_has_pgdata "${PG_VOL}"; then
    echo "${PG_VOL}"
    return 0
  fi
  if volume_has_pgdata "${PG_LEGACY_VOL}"; then
    log "检测到历史数据卷 ${PG_LEGACY_VOL:0:12}...，将复用（避免空库）"
    echo "${PG_LEGACY_VOL}"
    return 0
  fi
  docker volume inspect "${PG_VOL}" >/dev/null 2>&1 || docker volume create "${PG_VOL}" >/dev/null
  echo "${PG_VOL}"
}

ensure_daemon() {
  # usage: ensure_daemon NAME NEEDLE SCRIPT LOG PIDFILE READY_URL [READY_PATTERN] [WAIT_SEC]
  local name="$1"
  local needle="$2"
  local script="$3"
  local logf="$4"
  local pidf="$5"
  local url="$6"
  local pattern="${7:-}"
  local wait_sec="${8:-40}"

  if watchdog_alive "${pidf}" "${needle}" && wait_http_ok "${url}" 2 "${pattern}"; then
    log "${name} 已在运行 (PID $(tr -d '[:space:]' <"${pidf}"))"
    return 0
  fi

  # 清理僵尸
  pkill -f "${needle}" 2>/dev/null || true
  sleep 1

  log "daemonize ${name} → ${logf}"
  "${GEOFLOW_SCRIPTS_ROOT}/daemonize.sh" "${script}" "${logf}" "${pidf}"

  if ! wait_http_ok "${url}" "${wait_sec}" "${pattern}"; then
    err "${name} 启动失败（${wait_sec}s 内无响应），尾日志："
    tail -30 "${logf}" 2>/dev/null || true
    return 1
  fi
  log "${name} 健康检查通过 PID=$(tr -d '[:space:]' <"${pidf}")"
  return 0
}

print_endpoints() {
  log "Postgres → :${PG_PORT}  库 geo_flow + gweb_db（ADR-017）"
  log "API   → http://127.0.0.1:${API_PORT}/health"
  log "Admin → http://127.0.0.1:${ADMIN_PORT}/login  (admin / password)"
  if pgrep -f "celery -A app.workers.celery_app worker" >/dev/null 2>&1; then
    log "Worker → 运行中（生产/评估/再扫队列）"
  else
    log "WARN Worker 未运行。本地请 ./scripts/start-worker.sh"
  fi
  if pgrep -f "celery -A app.workers.celery_app beat" >/dev/null 2>&1; then
    log "Beat   → 运行中（日扫/周扫/再扫）"
  else
    log "WARN Beat 未运行。本地请 ./scripts/start-beat.sh"
  fi
  log "日志  → API:${GEOFLOW_API_LOG} Admin:${GEOFLOW_ADMIN_LOG} Worker:${GEOFLOW_WORKER_LOG} Beat:${GEOFLOW_BEAT_LOG}"
}
