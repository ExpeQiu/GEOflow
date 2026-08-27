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
  AUTH_H="Authorization: Bearer $TOKEN"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/settings/site" -H "$AUTH_H" >/dev/null && log "Admin site settings OK" || log "WARN: site settings 未就绪（需 alembic 002+）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/settings/admins" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d and 'current_admin_id' in d" 2>/dev/null && log "Admin settings admins OK" || log "WARN: settings/admins 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/settings/api-tokens" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d" 2>/dev/null && log "Admin settings api-tokens OK" || log "WARN: settings/api-tokens 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/settings/security/sensitive-words" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'words' in d" 2>/dev/null && log "Admin settings security OK" || log "WARN: settings/security 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/settings/activity-logs" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d" 2>/dev/null && log "Admin activity-logs OK" || log "WARN: activity-logs 未就绪"
  UP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${API_PORT}/uploads/__missing__")
  if [ "$UP_CODE" = "401" ] || [ "$UP_CODE" = "403" ]; then
    log "uploads auth gate OK (${UP_CODE})"
  else
    log "WARN: uploads 未鉴权 (got ${UP_CODE})"
  fi
  CB_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:${API_PORT}/internal/content-agent/callback" \
    -H "Content-Type: application/json" -d '{"request_id":"x","workflow_type":"content","status":"success"}')
  if [ "$CB_CODE" = "401" ] || [ "$CB_CODE" = "503" ]; then
    log "content-agent callback signature gate OK (${CB_CODE})"
  else
    log "WARN: content-agent callback 未强制签名 (got ${CB_CODE})"
  fi
  WS_CODE=$(python3 - <<'PY'
import asyncio, sys
try:
    import websockets
except ImportError:
    print("skip")
    sys.exit(0)
async def main():
    try:
        async with websockets.connect("ws://127.0.0.1:%s/ws/admin/tasks" % (__import__("os").environ.get("API_PORT","18081")), open_timeout=2):
            print("open")
    except Exception as e:
        print(type(e).__name__)
asyncio.run(main())
PY
)
  if [ "$WS_CODE" = "skip" ]; then
    log "SKIP ws auth check (no websockets pkg)"
  elif echo "$WS_CODE" | grep -qiE 'InvalidStatus|ConnectionClosed|401|403|open'; then
    # 无 token 应无法正常订阅；open 表示仍可连上（需人工确认）
    if [ "$WS_CODE" = "open" ]; then
      log "WARN: ws 无 token 仍可连接"
    else
      log "ws auth gate OK (${WS_CODE})"
    fi
  else
    log "ws auth probe result=${WS_CODE}"
  fi
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/materials/title-libraries" -H "$AUTH_H" >/dev/null && log "Admin title-libraries OK" || log "WARN: title-libraries 未就绪（需 alembic 002）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/materials/keyword-libraries" -H "$AUTH_H" >/dev/null && log "Admin keyword-libraries OK" || log "WARN: keyword-libraries 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor" -H "$AUTH_H" >/dev/null && log "Admin strategy monitor OK" || log "WARN: strategy monitor 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/knowledge-settings" -H "$AUTH_H" >/dev/null && log "Admin knowledge-settings OK" || log "WARN: knowledge-settings 未就绪（需 alembic 004）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/ai-models" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d and 'vendors' in d" 2>/dev/null && log "Admin ai-models gateway catalog OK" || log "WARN: ai-models 网关字段未就绪（需 alembic 019）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/ai-gateway" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'mode' in d and 'probe' in d" 2>/dev/null && log "Admin ai-gateway probe OK" || log "WARN: ai-gateway 未就绪（Lobster :56045 可选）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/ai-gateway" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'mode' in d" 2>/dev/null && log "Admin ai-gateway OK" || log "WARN: ai-gateway 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/wiki" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'pages' in d and 'stats' in d" 2>/dev/null && log "Admin wiki editor OK" || log "WARN: wiki editor 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/wiki/related-options" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d" 2>/dev/null && log "Admin wiki related-options OK" || log "WARN: wiki related-options 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/wiki/packs" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'packs' in d" 2>/dev/null && log "Admin wiki packs OK" || log "WARN: wiki packs 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/wiki/reconcile" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'stats' in d" 2>/dev/null && log "Admin wiki reconcile OK" || log "WARN: wiki reconcile 未就绪（需 GEOweb :3070）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'recent_probes' in d" 2>/dev/null && log "Admin monitor probes OK" || log "WARN: monitor probes 未就绪（需 alembic 005）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/settings" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'probe_mode' in d" 2>/dev/null && log "Admin monitor settings OK" || log "WARN: monitor settings 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/runs" -H "$AUTH_H" >/dev/null && log "Admin monitor runs OK" || log "WARN: monitor runs 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/scenes" -H "$AUTH_H" >/dev/null && log "Admin monitor scenes OK" || log "WARN: AIVIS scenes 未就绪（需 alembic 007）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/templates" -H "$AUTH_H" >/dev/null && log "Admin monitor templates OK" || log "WARN: AIVIS templates 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/competitors" -H "$AUTH_H" >/dev/null && log "Admin monitor competitors OK" || log "WARN: AIVIS competitors 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/snapshots" -H "$AUTH_H" >/dev/null && log "Admin monitor snapshots OK" || log "WARN: AIVIS snapshots 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/insights" -H "$AUTH_H" >/dev/null && log "Admin monitor insights OK" || log "WARN: AIVIS insights 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/reports" -H "$AUTH_H" >/dev/null && log "Admin monitor reports OK" || log "WARN: AIVIS reports 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/competitor-matrix" -H "$AUTH_H" >/dev/null && log "Admin competitor matrix OK" || log "WARN: competitor matrix 未就绪"
  curl -sf -X POST "http://127.0.0.1:${API_PORT}/api/admin/strategy/framework/scan" -H "$AUTH_H" -H "Content-Type: application/json" \
    -d '{"sync":true,"limit":1,"platforms":["deepseek"]}' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert d.get('scan_type')=='framework_api'" 2>/dev/null && log "Admin framework scan OK" || log "WARN: framework scan 未就绪（需 alembic 018 + AI_MOCK_MODE）"
  curl -sf -X POST "http://127.0.0.1:${API_PORT}/api/admin/strategy/citation/scan" -H "$AUTH_H" -H "Content-Type: application/json" \
    -d '{"sync":true,"limit":1,"platforms":["kimi"]}' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert d.get('scan_type')=='citation_grounded'" 2>/dev/null && log "Admin citation scan OK" || log "WARN: citation scan 未就绪（需 alembic 018 + AI_MOCK_MODE）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/cross-track" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'items' in d and 'summary' in d" 2>/dev/null && log "Admin cross-track OK" || log "WARN: cross-track 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/remediations" -H "$AUTH_H" >/dev/null && log "Admin remediations OK" || log "WARN: remediations 未就绪（需 alembic 012）"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/gweb-alignment" -H "$AUTH_H" >/dev/null && log "Admin gweb-alignment OK" || log "WARN: gweb-alignment 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/settings" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'strict_api' in d and 'remediation_delay_hours' in d" 2>/dev/null && log "Admin closed-loop settings OK" || log "WARN: closed-loop settings 字段缺失"
  LEGACY_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "http://127.0.0.1:${API_PORT}/api/admin/strategy/monitor/scenes/1/create-task?legacy_direct_task=true" \
    -H "$AUTH_H")
  if [ "$LEGACY_CODE" = "410" ]; then
    log "legacy_direct_task 410 OK"
  else
    log "WARN: legacy_direct_task 未返回 410 (got ${LEGACY_CODE})"
  fi
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/distribution/form-options" -H "$AUTH_H" \
    | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert d.get('channel_types')==['geoweb']" 2>/dev/null \
    && log "distribution form geoweb-only OK" || log "WARN: 渠道默认未收敛到 geoweb"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/knowledge-bases/embedding-ready" -H "$AUTH_H" \
    | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('  embedding mode=%s ready=%s' % (d.get('mode'), d.get('ready')))" \
    && log "embedding-ready OK" || log "WARN: embedding-ready 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/knowledge-bases/techstore-preview?source=fixture" -H "$AUTH_H" \
    | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert 'kb_names' in d and d.get('source')=='fixture'" 2>/dev/null \
    && log "Admin techstore-preview fixture OK" || log "WARN: techstore-preview 未就绪"
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/knowledge-bases/rag-sandbox" -H "$AUTH_H" -H "Content-Type: application/json" -d '{"knowledge_base_id":1,"query":"test","limit":3}' >/dev/null 2>&1 && log "Admin RAG sandbox OK" || log "WARN: RAG sandbox 跳过（需知识库数据）"
  if pgrep -f "celery -A app.workers.celery_app worker" >/dev/null 2>&1 \
    || docker ps --filter "name=geoflow-v3-worker" --filter "status=running" --format '{{.Names}}' 2>/dev/null | grep -q .; then
    python3 "${ROOT}/scripts/smoke_kb_content.py" && log "KB→内容小闭环 smoke OK" || log "WARN: KB→内容小闭环 smoke 失败"
  else
    log "FAIL: Celery worker 未运行（本地 ./scripts/start-worker.sh 或 docker compose worker）"
    exit 1
  fi
  curl -sf "http://127.0.0.1:${API_PORT}/api/admin/agents" -H "$AUTH_H" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; assert len(d.get('items',[]))>=1" 2>/dev/null && log "Admin agents OK" || log "WARN: agents 配置未就绪"
else
  log "WARN: Admin 登录失败（请先 seed）"
fi

if curl -sf "http://127.0.0.1:${ADMIN_PORT}/" >/dev/null 2>&1; then
  log "geoflow-admin OK (:${ADMIN_PORT})"
else
  log "WARN: geoflow-admin 未响应（可能仍在构建）"
fi

log "验证完成"
