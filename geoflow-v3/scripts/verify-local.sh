#!/usr/bin/env bash
# 本地验证（无需 Docker）：pytest + 结构检查
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
ADMIN="${ROOT}/apps/geoflow-admin"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
PASS=0
FAIL=0

check() {
  if eval "$2"; then
    log "OK  $1"
    PASS=$((PASS + 1))
  else
    log "FAIL $1"
    FAIL=$((FAIL + 1))
  fi
}

log "=== GEOFlow v3 本地验证 ==="

check "backend/app/main.py" "[ -f '${BACKEND}/app/main.py' ]"
check "docker-compose.yml" "[ -f '${ROOT}/docker-compose.yml' ]"
check "geoflow-admin package.json" "[ -f '${ADMIN}/package.json' ]"
check "alembic migration" "[ -f '${BACKEND}/alembic/versions/001_initial_schema.py' ]"
check "LangGraph config" "[ -f '${BACKEND}/app/ai/config/workflows.yml' ]"
check "lifecycle scripts" "[ -x '${ROOT}/scripts/start.sh' ] && [ -x '${ROOT}/scripts/verify.sh' ]"

if [ -x "${BACKEND}/.venv/bin/python" ]; then
  # 与 verification-report 对齐的收口冒烟；全量 tests/ 含环境依赖项不作为本脚本门禁
  if (cd "${BACKEND}" && .venv/bin/python -m pytest -q \
      tests/test_product_trim.py \
      tests/test_techstore_knowledge_import.py \
      tests/test_theme_pack_produce.py::test_mining_prompt_injects_compare_dims \
      tests/test_north_star_kpi.py \
      tests/test_platform_uat.py -m "not live"); then
    log "OK  pytest (product-trim / techstore-import / mining inject / north-star)"
    PASS=$((PASS + 1))
  else
    log "FAIL pytest"
    FAIL=$((FAIL + 1))
  fi
else
  log "SKIP pytest（无 .venv，请 cd backend && python3 -m venv .venv && pip install -e .）"
fi

log "--- 结果: ${PASS} 通过, ${FAIL} 失败 ---"
[ "${FAIL}" -eq 0 ]
