#!/usr/bin/env bash
# 腾讯云远端：与 Gweb/Techstore 同一套资源。
# Docker 只保留 backend-backend-1 / backend-db-1；库走 127.0.0.1:5433。
set -euo pipefail

GEOFLOW="/opt/geoflow"
ADMIN="/opt/geoflow-admin"
GEOWEB="/opt/geoweb"
ENV_FILE="${GEOFLOW}/.env"
GEOWEB_PUBLIC="${GEOWEB_PUBLIC:-http://111.230.58.40:8093}"
GEOFLOW_PUBLIC="${GEOFLOW_PUBLIC:-http://111.230.58.40:8098}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "停掉多余 Docker（geoflow postgres/redis），不动 backend-*"
docker rm -f geoflow-v3-postgres geoflow-v3-redis 2>/dev/null || true
rm -rf /opt/geoflow-data

TS_DB="$(grep -E '^DATABASE_URL=' /opt/techstore/.env 2>/dev/null | head -1 | cut -d= -f2- || true)"
TS_REV="$(grep -E '^GWEB_REVALIDATE_SECRET=' /opt/techstore/.env 2>/dev/null | head -1 | cut -d= -f2- || echo gweb-revalidate-2026-prod)"
if [[ -z "$TS_DB" ]]; then
  echo "ERROR: 读不到 /opt/techstore/.env DATABASE_URL" >&2
  exit 1
fi

FLOW_ASYNC_URL="$(python3 - <<PY
from urllib.parse import urlparse, urlunparse
u = urlparse("""${TS_DB}""".strip())
print(urlunparse(u._replace(scheme="postgresql+asyncpg", path="/geo_flow", query="")))
PY
)"
FLOW_DB_URL="$(python3 - <<PY
from urllib.parse import urlparse, urlunparse
u = urlparse("""${TS_DB}""".strip())
print(urlunparse(u._replace(path="/geo_flow")))
PY
)"

log "确保 5433 上有 geo_flow 库（与 gweb_db 同实例）"
if ! docker exec backend-db-1 psql -U miniprogram -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='geo_flow'" | grep -q 1; then
  docker exec backend-db-1 psql -U miniprogram -d postgres -c "CREATE DATABASE geo_flow OWNER miniprogram;"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  JWT="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  CB="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  SYNC="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
else
  JWT="$(grep -E '^JWT_SECRET=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
  CB="$(grep -E '^CONTENT_AGENT_CALLBACK_SECRET=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
  SYNC="$(grep -E '^GEOWEB_SYNC_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
  [[ -n "$JWT" ]] || JWT="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  [[ -n "$CB" ]] || CB="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  [[ -n "$SYNC" ]] || SYNC="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
fi

cat > "$ENV_FILE" <<EOF
DEBUG=false
ALLOW_INSECURE_JWT=false
AI_MOCK_MODE=true
SKIP_PGVECTOR=true
GEOFLOW_TECH_BRAND_MODE=true
GEOFLOW_PUBLIC_SITE_ENABLED=false
DATABASE_URL=${FLOW_ASYNC_URL}
DATABASE_URL_SYNC=${FLOW_DB_URL}
REDIS_URL=memory://
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
JWT_SECRET=${JWT}
CONTENT_AGENT_CALLBACK_SECRET=${CB}
CORS_ALLOWED_ORIGINS=${GEOFLOW_PUBLIC},http://127.0.0.1:3015
GEOWEB_BASE_URL=http://127.0.0.1:3014
GEOWEB_SYNC_TOKEN=${SYNC}
GEOWEB_SYNC_ENABLED=true
TECHSTORE_DATABASE_URL=${TS_DB}
UPLOAD_PATH=/opt/geoflow/backend/storage/uploads
LLM_GATEWAY_MODE=auto
EOF
chmod 600 "$ENV_FILE"

cat > "${GEOWEB}/.env" <<EOF
NODE_ENV=production
PORT=3014
HOSTNAME=0.0.0.0
NEXT_PUBLIC_SITE_URL=${GEOWEB_PUBLIC}
AI_MOCK_MODE=true
DATABASE_URL=${TS_DB}
GEOFLOW_SYNC_TOKEN=${SYNC}
GWEB_REVALIDATE_SECRET=${TS_REV}
TECHSTORE_PUBLIC_URL=http://127.0.0.1:3013
QUESTIONS_STORE_PATH=storage/questions
NEXT_TELEMETRY_DISABLED=1
EOF
chmod 600 "${GEOWEB}/.env"

mkdir -p "${GEOFLOW}/backend/storage/uploads" "${GEOWEB}/storage/questions" \
  "${GEOWEB}/logs" "${ADMIN}/logs" "${GEOFLOW}/logs"

log "Python venv + 依赖"
if [[ ! -x /opt/geoflow/venv/bin/python ]]; then
  if ! python3 -m venv /opt/geoflow/venv; then
    dnf install -y python3-pip python3-devel gcc >/dev/null 2>&1 || true
    python3 -m venv /opt/geoflow/venv
  fi
fi
/opt/geoflow/venv/bin/pip install -q -U pip
/opt/geoflow/venv/bin/pip install -q --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
  -e "/opt/geoflow/backend"

log "alembic + seed（SKIP_PGVECTOR，5433/geo_flow）"
cd /opt/geoflow/backend
set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a
export PYTHONPATH=/opt/geoflow/backend SKIP_PGVECTOR=true
/opt/geoflow/venv/bin/alembic upgrade head
/opt/geoflow/venv/bin/python scripts/seed.py

log "PM2：geoflow-api / geoflow-admin / geoweb（不动 gweb/techstore；不起 worker）"
start_pm2() {
  local name="$1"
  if pm2 describe "$name" >/dev/null 2>&1; then
    pm2 delete "$name" || true
  fi
}
start_pm2 geoflow-api
start_pm2 geoflow-worker
start_pm2 geoflow-admin
start_pm2 geoweb

cat > /opt/geoflow/run-api.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
source /opt/geoflow/.env
set +a
export PYTHONPATH=/opt/geoflow/backend SKIP_PGVECTOR=true
cd /opt/geoflow/backend
exec /opt/geoflow/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18081 --workers 1
SH
chmod +x /opt/geoflow/run-api.sh

pm2 start /opt/geoflow/run-api.sh --name geoflow-api \
  --interpreter bash \
  --max-memory-restart 400M \
  --error /opt/geoflow/logs/api.err.log \
  --output /opt/geoflow/logs/api.out.log \
  --time

PORT=3015 HOSTNAME=0.0.0.0 NODE_ENV=production \
  pm2 start /opt/geoflow-admin/server.js --name geoflow-admin \
  --cwd /opt/geoflow-admin \
  --max-memory-restart 280M \
  --error /opt/geoflow-admin/logs/err.log \
  --output /opt/geoflow-admin/logs/out.log \
  --time

set -a
# shellcheck disable=SC1091
source /opt/geoweb/.env
set +a
export PORT=3014 HOSTNAME=0.0.0.0 NODE_ENV=production
cd /opt/geoweb
pm2 start /opt/geoweb/server.js --name geoweb \
  --cwd /opt/geoweb \
  --max-memory-restart 350M \
  --error /opt/geoweb/logs/err.log \
  --output /opt/geoweb/logs/out.log \
  --time

pm2 save
pm2 list
log "bootstrap 完成"
