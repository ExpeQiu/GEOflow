#!/usr/bin/env bash
# 一键 Docker 部署 GEOFlow + Techstore + GEOweb（共享 Postgres 两库，ADR-017）
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib.sh
source "${STACK_ROOT}/_lib.sh"

log "===== geo-stack start ====="
require_dirs || exit 1
require_cmd() {
  command -v docker >/dev/null 2>&1 || { err "需要 docker"; exit 1; }
  command -v curl >/dev/null 2>&1 || { err "需要 curl"; exit 1; }
}
require_cmd

if [[ ! -f "${STACK_ROOT}/.env" && -f "${STACK_ROOT}/.env.example" ]]; then
  cp "${STACK_ROOT}/.env.example" "${STACK_ROOT}/.env"
  log "已创建 deploy-stack/.env"
fi
if [[ -f "${STACK_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${STACK_ROOT}/.env"
  set +a
fi

export GEOWEB_BASE_URL="${GEOWEB_BASE_URL:-http://geoweb:3000}"
export GEOWEB_SYNC_TOKEN="${GEOFLOW_SYNC_TOKEN:-dev-geoweb-sync-token}"
export GEOFLOW_SYNC_TOKEN="${GEOFLOW_SYNC_TOKEN:-dev-geoweb-sync-token}"
export TECHSTORE_DATABASE_URL="${TECHSTORE_DATABASE_URL:-postgresql://geo_user:geo_password@postgres:5432/gweb_db}"

log "1/3 GEOFlow（含 Postgres + Redis）"
"${GEOFLOW_V3_ROOT}/scripts/start.sh"

log "2/3 Techstore"
(cd "${TECHSTORE_ROOT}" && ./start.sh docker)

log "3/3 GEOweb"
(cd "${GEOWEB_ROOT}" && ./scripts/start.sh docker)

if ! "${STACK_ROOT}/verify.sh"; then
  err "验收未通过"
  exit 1
fi

log "全部就绪"
log "  GEOFlow API  http://127.0.0.1:${API_PORT}/health"
log "  Admin        http://127.0.0.1:${ADMIN_PORT}/login"
log "  Techstore    http://127.0.0.1:${TECHSTORE_PORT}/admin"
log "  GEOweb       http://127.0.0.1:${GEOWEB_PORT}/"
log "===== geo-stack start 完成 ====="
