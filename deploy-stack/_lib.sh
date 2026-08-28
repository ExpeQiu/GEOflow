#!/usr/bin/env bash
# 三仓 Docker 路径解析（被 start/stop/verify source）
STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEOFLOW_ROOT="$(cd "${STACK_ROOT}/.." && pwd)"
: "${GEOFLOW_V3_ROOT:=${GEOFLOW_ROOT}/geoflow-v3}"
: "${TECHSTORE_ROOT:=$(cd "${GEOFLOW_ROOT}/../Techstore" 2>/dev/null && pwd || true)}"
: "${GEOWEB_ROOT:=$(cd "${GEOFLOW_ROOT}/../GEOweb" 2>/dev/null && pwd || true)}"

API_PORT="${API_PORT:-18081}"
ADMIN_PORT="${ADMIN_PORT:-13001}"
TECHSTORE_PORT="${TECHSTORE_PORT:-3001}"
GEOWEB_PORT="${GEOWEB_PORT:-3070}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
err() { log "ERROR: $*"; }

require_dirs() {
  local missing=0
  if [[ ! -d "${GEOFLOW_V3_ROOT}" ]]; then
    err "未找到 GEOFlow v3: ${GEOFLOW_V3_ROOT}"
    missing=1
  fi
  if [[ ! -d "${TECHSTORE_ROOT}" ]]; then
    err "未找到 Techstore: 期望 ${GEOFLOW_ROOT}/../Techstore （可用 TECHSTORE_ROOT 覆盖）"
    missing=1
  fi
  if [[ ! -d "${GEOWEB_ROOT}" ]]; then
    err "未找到 GEOweb: 期望 ${GEOFLOW_ROOT}/../GEOweb （可用 GEOWEB_ROOT 覆盖）"
    missing=1
  fi
  return "${missing}"
}

wait_http() {
  local url="$1" timeout="${2:-90}" needle="${3:-}"
  local i=0 body
  while (( i < timeout )); do
    if [[ -n "${needle}" ]]; then
      body="$(curl -sf --max-time 2 "${url}" 2>/dev/null || true)"
      if echo "${body}" | grep -q "${needle}"; then
        return 0
      fi
    elif curl -sf --max-time 2 -o /dev/null "${url}" 2>/dev/null; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}
