#!/usr/bin/env bash
# 本地开发启动（无需 pgvector 镜像）：PostgreSQL + 宿主机 Redis + API
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"
BACKEND="${ROOT}/backend"

cd "$ROOT"
: >"${GEOFLOW_START_LOG}"
log "===== start-local 开始 ====="

require_cmd docker curl python3 || exit 1

[ -f .env ] || cp .env.example .env

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
API_PORT=${API_PORT}
ADMIN_PORT=${ADMIN_PORT}
EOF
set -a
# shellcheck disable=SC1091
source .env.local
set +a

if ! redis_ok; then
  err "Redis 未就绪 (127.0.0.1:6379)。请先启动: brew services start redis"
  exit 1
fi
log "Redis OK"

# --- PostgreSQL：永不 rm 重建；优先复用容器与含数据的卷 ---
log "启动 PostgreSQL (${PG_NAME} :${PG_PORT})..."
if docker ps --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  log "PostgreSQL 已在运行"
elif docker ps -a --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  log "重启已有 PostgreSQL 容器（保留数据卷）..."
  docker start "${PG_NAME}" >/dev/null
else
  if ! docker image inspect postgres:16-alpine >/dev/null 2>&1; then
    err "本地无镜像 postgres:16-alpine。请先拉取或改用已有镜像。"
    exit 1
  fi
  VOL="$(resolve_pg_volume)"
  log "新建容器并挂载卷: ${VOL}"
  docker run -d --name "${PG_NAME}" \
    --restart unless-stopped \
    -e POSTGRES_DB=geo_flow \
    -e POSTGRES_USER=geo_user \
    -e POSTGRES_PASSWORD=geo_password \
    -p "127.0.0.1:${PG_PORT}:5432" \
    -v "${VOL}:/var/lib/postgresql/data" \
    postgres:16-alpine >/dev/null
fi

if ! wait_pg_ready "${PG_NAME}" 40; then
  err "PostgreSQL 未就绪，见: docker logs ${PG_NAME}"
  docker logs --tail 40 "${PG_NAME}" 2>&1 || true
  exit 1
fi
log "PostgreSQL ready"
docker inspect "${PG_NAME}" --format '挂载卷={{range .Mounts}}{{.Name}}{{end}}' 2>/dev/null | while read -r line; do log "${line}"; done

log "Python 依赖..."
if [ ! -x "${BACKEND}/.venv/bin/python" ]; then
  python3 -m venv "${BACKEND}/.venv"
  "${BACKEND}/.venv/bin/pip" install -q \
    fastapi uvicorn sqlalchemy asyncpg psycopg2-binary alembic greenlet \
    pydantic pydantic-settings "python-jose[cryptography]" bcrypt httpx pyyaml structlog pgvector \
    python-multipart celery redis passlib
fi

log "数据库迁移 + seed（seed 幂等，不会清空业务表）..."
cd "${BACKEND}"
export SKIP_PGVECTOR=true PYTHONPATH=.
export DATABASE_URL="postgresql+asyncpg://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow"
export DATABASE_URL_SYNC="postgresql://geo_user:geo_password@127.0.0.1:${PG_PORT}/geo_flow"
find alembic app -name '._*' -delete 2>/dev/null || true
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed.py

# 数据指纹（排查是否空库）
ARTICLES="$(docker exec "${PG_NAME}" psql -U geo_user -d geo_flow -tAc 'SELECT count(*) FROM articles' 2>/dev/null || echo '?')"
SCENES="$(docker exec "${PG_NAME}" psql -U geo_user -d geo_flow -tAc 'SELECT count(*) FROM geo_monitor_scenes' 2>/dev/null || echo '?')"
log "数据指纹: articles=${ARTICLES} scenes=${SCENES}"

log "启动 API :${API_PORT}..."
# 若健康则复用；否则清理本项目 API 后再 daemonize
if wait_http_ok "http://127.0.0.1:${API_PORT}/health" 2 "ok" \
  && watchdog_alive "${GEOFLOW_API_PID}" "run-api-watchdog.sh"; then
  log "API 已在运行 (PID $(tr -d '[:space:]' <"${GEOFLOW_API_PID}"))"
else
  pkill -f "uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}" 2>/dev/null || true
  ensure_daemon \
    "API" \
    "run-api-watchdog.sh" \
    "${ROOT}/scripts/run-api-watchdog.sh" \
    "${GEOFLOW_API_LOG}" \
    "${GEOFLOW_API_PID}" \
    "http://127.0.0.1:${API_PORT}/health" \
    "ok" \
    40
fi

print_endpoints
log "===== start-local 完成 ====="
