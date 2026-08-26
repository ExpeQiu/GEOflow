#!/usr/bin/env bash
# 六平台探针 Key 矩阵：缺 Key 跳过，不阻断主栈 verify。
# 真 UAT：export GEOFLOW_LIVE_PROBE=1 且配置对应 API Key。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-18081}"
API="http://127.0.0.1:${API_PORT}"

log() { echo "[probe-keys] $*"; }

TOKEN=$(curl -sf -X POST "${API}/api/v1/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || true)

if [ -z "${TOKEN:-}" ]; then
  log "SKIP: Admin 登录失败"
  exit 0
fi

AUTH="Authorization: Bearer ${TOKEN}"

log "=== Open API 平台（豆包 / DeepSeek / Kimi）==="
check_env() {
  local name="$1"
  if [ -n "${!name:-}" ]; then
    log "  ${name}=set"
  else
    log "  ${name}=missing (skip live)"
  fi
}
check_env DEEPSEEK_API_KEY
check_env DOUBAO_API_KEY
check_env ARK_API_KEY
check_env DOUBAO_MODEL
check_env KIMI_API_KEY

log "=== C 端辅轨（通义 / 文心 / 元宝，无 Open API Key）==="
log "  CEND_MOCK_MODE=${CEND_MOCK_MODE:-unset}  CEND_SCAN_PLATFORMS=${CEND_SCAN_PLATFORMS:-yuanbao}"
log "  真扫需 pip install -e '.[cend]' + playwright + 登录 Profile"

if [ "${GEOFLOW_LIVE_PROBE:-}" = "1" ]; then
  log "GEOFLOW_LIVE_PROBE=1 → pytest live"
  cd "${ROOT}/backend"
  .venv/bin/python -m pytest -q tests/test_platform_uat.py -m live --tb=line || {
    log "WARN: live probe 未全绿（缺 Key 或平台失败）"
    exit 0
  }
else
  log "默认只跑门禁矩阵（无 live 调用）。真 Key：GEOFLOW_LIVE_PROBE=1 $0"
  cd "${ROOT}/backend"
  .venv/bin/python -m pytest -q tests/test_platform_uat.py -m "not live" --tb=line
fi

log "完成"
