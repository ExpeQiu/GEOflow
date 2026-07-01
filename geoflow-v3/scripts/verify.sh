#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API_PORT="${API_PORT:-18081}"
ADMIN_PORT="${ADMIN_PORT:-13001}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Docker 运行态"
docker compose ps

if curl -sf "http://127.0.0.1:${API_PORT}/health" | grep -q ok; then
  log "API health OK (:${API_PORT})"
else
  log "WARN: API health 未响应"
  exit 1
fi

TOKEN=$(curl -sf -X POST "http://127.0.0.1:${API_PORT}/api/v1/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || true)

if [ -n "${TOKEN:-}" ]; then
  log "Admin JWT 登录 OK"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/dashboard" -H "Authorization: Bearer $TOKEN" >/dev/null && log "Admin dashboard OK"
else
  log "WARN: Admin 登录失败（请先 seed）"
fi

if curl -sf "http://127.0.0.1:${ADMIN_PORT}/" >/dev/null 2>&1; then
  log "geoflow-admin OK (:${ADMIN_PORT})"
else
  log "WARN: geoflow-admin 未响应（可能仍在构建）"
fi

log "验证完成"
