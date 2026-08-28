#!/usr/bin/env bash
# 一键栈健康检查：两库 + 三站 HTTP
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib.sh
source "${STACK_ROOT}/_lib.sh"

log "===== geo-stack verify ====="
fail=0

check() {
  local name="$1" url="$2" needle="${3:-}"
  if wait_http "${url}" 5 "${needle}"; then
    log "ok ${name} ${url}"
  else
    err "FAIL ${name} ${url}"
    fail=1
  fi
}

check "GEOFlow API" "http://127.0.0.1:${API_PORT}/health" "ok"
check "GEOFlow Admin" "http://127.0.0.1:${ADMIN_PORT}/"
check "Techstore" "http://127.0.0.1:${TECHSTORE_PORT}/api/health"
check "GEOweb" "http://127.0.0.1:${GEOWEB_PORT}/"

ctn=""
ctn="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E '^geoflow-v3-postgres$' | head -1 || true)"
if [[ -z "${ctn}" ]]; then
  err "FAIL postgres 容器未运行"
  fail=1
else
  for db in geo_flow gweb_db; do
    if docker exec "${ctn}" psql -U geo_user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" 2>/dev/null | grep -q 1; then
      log "ok database ${db}"
    else
      err "FAIL 缺少 database ${db}"
      fail=1
    fi
  done
fi

if [[ "${fail}" != "0" ]]; then
  err "verify 未通过"
  exit 1
fi
log "===== geo-stack verify 通过 ====="
