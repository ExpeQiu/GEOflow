#!/usr/bin/env bash
# 本地开发启动（无需 pgvector 镜像）：PostgreSQL + 宿主机 Redis + uvicorn
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
PG_NAME="geoflow-v3-postgres-local"
PG_PORT="${PG_PORT:-15433}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

cd "$ROOT"
[ -f .env ] || cp .env.example .env

# 本地 .env 覆盖
cat > .env.local <<EOF
DATABASE_URL=postgresql+asyncpg://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow
DATABASE_URL_SYNC=postgresql://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
SKIP_PGVECTOR=true
AI_MOCK_MODE=true
DEBUG=true
GWEB_BASE_URL=http://127.0.0.1:3000
GWEB_REVALIDATE_SECRET=shared-revalidate-secret
GWEB_SYNC_ENABLED=true
EOF
export $(grep -v '^#' .env.local | xargs)

log "启动 PostgreSQL (postgres:16-alpine :${PG_PORT})..."
if ! docker ps --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  docker rm -f "${PG_NAME}" 2>/dev/null || true
  docker run -d --name "${PG_NAME}" \
    -e POSTGRES_DB=geo_flow \
    -e POSTGRES_USER=geo_user \
    -e POSTGRES_PASSWORD=geo_password \
    -p "127.0.0.1:${PG_PORT}:5432" \
    postgres:16-alpine
  sleep 4
fi

log "Python 依赖..."
if [ ! -x "${BACKEND}/.venv/bin/python" ]; then
  python3 -m venv "${BACKEND}/.venv"
  "${BACKEND}/.venv/bin/pip" install -q \
    fastapi uvicorn sqlalchemy asyncpg psycopg2-binary alembic greenlet \
    pydantic pydantic-settings "python-jose[cryptography]" bcrypt httpx pyyaml structlog pgvector \
    python-multipart celery redis passlib
fi

log "数据库迁移 + seed..."
cd "${BACKEND}"
export SKIP_PGVECTOR=true
export PYTHONPATH=.
find alembic app -name '._*' -delete 2>/dev/null || true
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed.py

log "启动 API :${API_PORT:-18081}..."
API_PORT="${API_PORT:-18081}"
if curl -sf "http://127.0.0.1:${API_PORT}/health" | grep -q ok 2>/dev/null; then
  log "API 已在运行 :${API_PORT}"
else
  pkill -f "uvicorn app.main:app.*127.0.0.1:${API_PORT}" 2>/dev/null || true
  pkill -f "run-api-watchdog.sh" 2>/dev/null || true
  sleep 1
  "${ROOT}/scripts/daemonize.sh" "${ROOT}/scripts/run-api-watchdog.sh" /tmp/geoflow-v3-api.log /tmp/geoflow-v3-api.pid
  API_PID=$(cat /tmp/geoflow-v3-api.pid)
  for _ in 1 2 3 4 5; do
    if curl -sf "http://127.0.0.1:${API_PORT}/health" | grep -q ok; then
      break
    fi
    sleep 1
  done
  if ! curl -sf "http://127.0.0.1:${API_PORT}/health" | grep -q ok; then
    log "ERROR: API 启动失败，见 /tmp/geoflow-v3-api.log"
    tail -20 /tmp/geoflow-v3-api.log
    exit 1
  fi
  log "API PID=${API_PID} 健康检查通过"
fi
log "完成 → http://127.0.0.1:${API_PORT:-18081}/health"
log "Admin 登录 → POST /api/v1/auth/admin-login"
