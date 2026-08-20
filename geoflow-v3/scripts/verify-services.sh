#!/usr/bin/env bash
# 本地服务验收（配合 start-local.sh）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-18081}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== GEOFlow v3 服务验证 ==="

"${ROOT}/scripts/verify-local.sh"

if curl -sf "http://127.0.0.1:${API_PORT}/health" | grep -q ok; then
  log "API /health OK"
else
  log "FAIL: API 未响应，请先 ./scripts/start-local.sh"
  exit 1
fi

TOKEN=$(curl -sf -X POST "http://127.0.0.1:${API_PORT}/api/v1/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || true)

if [ -n "${TOKEN:-}" ]; then
  log "Admin JWT 登录 OK"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/dashboard" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('  dashboard: tasks=%s version=%s' % (d.get('tasks_count'), d.get('version')))"
else
  log "WARN: 登录失败"
  exit 1
fi

# API Token 登录
API_TOKEN=$(curl -sf -X POST "http://127.0.0.1:${API_PORT}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || true)
if [ -n "${API_TOKEN:-}" ]; then
  log "API v1 Token 登录 OK"
  curl -sf "http://127.0.0.1:${API_PORT}/api/v1/catalog" -H "Authorization: Bearer $API_TOKEN" >/dev/null && log "  catalog OK"
fi

docker ps --filter "name=geoflow-v3-postgres-local" --format "  postgres: {{.Status}}" 2>/dev/null || true

ADMIN_PORT="${ADMIN_PORT:-13001}"
if curl -sf "http://127.0.0.1:${ADMIN_PORT}/login" >/dev/null 2>&1; then
  PROXY_TOKEN=$(curl -sf -X POST "http://127.0.0.1:${ADMIN_PORT}/api/v1/auth/admin-login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"password"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || true)
  if [ -n "${PROXY_TOKEN:-}" ]; then
    log "Admin 前端代理登录 OK (http://127.0.0.1:${ADMIN_PORT}/api/...)"
  else
    log "WARN: Admin 前端代理登录失败，请重启 ./scripts/start-admin.sh"
    exit 1
  fi
else
  log "WARN: Admin 未运行 (http://127.0.0.1:${ADMIN_PORT})，跳过前端代理验证"
fi

if pgrep -f "celery -A app.workers.celery_app worker" >/dev/null 2>&1 \
  || docker ps --filter "name=geoflow-v3-worker" --filter "status=running" --format '{{.Names}}' 2>/dev/null | grep -q .; then
  log "Celery worker OK"
else
  log "FAIL: Celery worker 未运行（./scripts/start-worker.sh）"
  exit 1
fi

log "验证完成 ✓"
