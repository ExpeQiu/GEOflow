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
  if (cd "${BACKEND}" && .venv/bin/python -m pytest tests/ -q); then
    log "OK  pytest ($(cd "${BACKEND}" && .venv/bin/python -m pytest tests/ --collect-only -q 2>/dev/null | tail -1))"
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
