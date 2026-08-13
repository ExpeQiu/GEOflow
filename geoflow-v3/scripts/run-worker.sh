#!/usr/bin/env bash
# Celery Worker（本地开发）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
if [[ -f "${ROOT}/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env.local"
  set +a
fi
PG_PORT="${PG_PORT:-15433}"
REDIS_PORT="${REDIS_PORT:-6379}"

cd "${BACKEND}"
exec env \
  PYTHONPATH=. \
  SKIP_PGVECTOR=true \
  AI_MOCK_MODE="${AI_MOCK_MODE:-true}" \
  GEOWEB_BASE_URL="${GEOWEB_BASE_URL:-http://127.0.0.1:3070}" \
  GEOWEB_SYNC_TOKEN="${GEOWEB_SYNC_TOKEN:-dev-sync-token}" \
  GEOWEB_SYNC_ENABLED="${GEOWEB_SYNC_ENABLED:-true}" \
  DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow}" \
  DATABASE_URL_SYNC="${DATABASE_URL_SYNC:-postgresql://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow}" \
  REDIS_URL="${REDIS_URL:-redis://127.0.0.1:${REDIS_PORT}/0}" \
  CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://127.0.0.1:${REDIS_PORT}/0}" \
  CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://127.0.0.1:${REDIS_PORT}/1}" \
  .venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q celery,geoflow --pool=solo
