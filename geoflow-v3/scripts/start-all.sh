#!/usr/bin/env bash
# 一键启动：PostgreSQL + Redis 检查 + API + Admin + Worker + Beat
# 无 Docker：GEOFLOW_NO_DOCKER=1 ./scripts/start-all.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"

log "===== start-all 开始 (no_docker=${GEOFLOW_NO_DOCKER:-0}) ====="

GEOFLOW_NO_DOCKER="${GEOFLOW_NO_DOCKER:-0}" "${ROOT}/scripts/start-local.sh"

log "启动 Admin (daemon)..."
GEOFLOW_ADMIN_DAEMON=1 "${ROOT}/scripts/start-admin.sh" --daemon

log "启动 Celery Worker + Beat..."
chmod +x "${ROOT}/scripts/start-worker.sh" "${ROOT}/scripts/start-beat.sh"
"${ROOT}/scripts/start-worker.sh"
"${ROOT}/scripts/start-beat.sh"

if ! "${ROOT}/scripts/verify-services.sh"; then
  err "验收未通过，请查看 ${GEOFLOW_START_LOG} / ${GEOFLOW_API_LOG} / ${GEOFLOW_ADMIN_LOG}"
  exit 1
fi

print_endpoints
log "===== start-all 完成 ====="
