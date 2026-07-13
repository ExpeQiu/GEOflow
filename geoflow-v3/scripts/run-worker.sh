#!/usr/bin/env bash
# Celery Worker（本地开发）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
PG_PORT="${PG_PORT:-15433}"
REDIS_PORT="${REDIS_PORT:-6379}"

cd "${BACKEND}"
exec env \
  PYTHONPATH=. \
  SKIP_PGVECTOR=true \
  AI_MOCK_MODE=true \
  GWEB_BASE_URL="${GWEB_BASE_URL:-http://127.0.0.1:3000}" \
  GWEB_REVALIDATE_SECRET="${GWEB_REVALIDATE_SECRET:-shared-revalidate-secret}" \
  GWEB_SYNC_ENABLED="${GWEB_SYNC_ENABLED:-true}" \
  DATABASE_URL="postgresql+asyncpg://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow" \
  DATABASE_URL_SYNC="postgresql://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow" \
  REDIS_URL="redis://127.0.0.1:${REDIS_PORT}/0" \
  CELERY_BROKER_URL="redis://127.0.0.1:${REDIS_PORT}/0" \
  CELERY_RESULT_BACKEND="redis://127.0.0.1:${REDIS_PORT}/1" \
  .venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q celery,geoflow --pool=solo
