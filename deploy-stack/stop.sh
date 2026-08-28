#!/usr/bin/env bash
# 停止三仓 Docker 应用；默认保留 Postgres 数据卷
#   ./stop.sh           停 GEOweb + Techstore + GEOFlow compose
#   ./stop.sh --apps    只停三个应用，保留 postgres/redis
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib.sh
source "${STACK_ROOT}/_lib.sh"

APPS_ONLY=0
[[ "${1:-}" == "--apps" ]] && APPS_ONLY=1

log "===== geo-stack stop ====="
require_dirs || exit 1

if [[ -d "${GEOWEB_ROOT}" ]]; then
  log "停止 GEOweb"
  (cd "${GEOWEB_ROOT}" && ./scripts/stop.sh docker) || true
fi
if [[ -d "${TECHSTORE_ROOT}" ]]; then
  log "停止 Techstore"
  (cd "${TECHSTORE_ROOT}" && ./stop.sh docker) || true
fi

if [[ "${APPS_ONLY}" == "1" ]]; then
  log "保留 Postgres/Redis（--apps）"
  if [[ -d "${GEOFLOW_V3_ROOT}" ]]; then
    (cd "${GEOFLOW_V3_ROOT}" && docker compose stop api worker scheduler flower geoflow-admin) || true
  fi
else
  log "停止 GEOFlow compose（含 Postgres）"
  (cd "${GEOFLOW_V3_ROOT}" && ./scripts/stop.sh) || true
fi

log "===== geo-stack stop 完成 ====="
