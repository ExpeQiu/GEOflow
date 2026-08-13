#!/usr/bin/env bash
# 独立 API 进程（供 start-local / nohup 调用）
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
API_PORT="${API_PORT:-18081}"

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
  REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}" \
  CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://127.0.0.1:6379/0}" \
  CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://127.0.0.1:6379/1}" \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}"
