#!/usr/bin/env bash
# 独立 API 进程（供 start-local / nohup 调用）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
PG_PORT="${PG_PORT:-15433}"
API_PORT="${API_PORT:-18081}"

cd "${BACKEND}"
exec env \
  PYTHONPATH=. \
  SKIP_PGVECTOR=true \
  AI_MOCK_MODE=true \
  DATABASE_URL="postgresql+asyncpg://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow" \
  DATABASE_URL_SYNC="postgresql://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow" \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}"
