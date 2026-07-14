#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
VERIFY_STORE="$ROOT/.verify-store.json"
rm -f "$VERIFY_STORE"

log()  { echo "[verify] $*"; }
ok()   { log "✓ $*"; PASS=$((PASS + 1)); }
fail() { log "✗ $*"; FAIL=$((FAIL + 1)); }

log "准备虚拟环境..."
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  python3 -m venv "$ROOT/.venv"
fi
PYTHON="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

run_cli() {
  if [[ -x "$ROOT/.venv/bin/ragc" ]]; then
    "$ROOT/.venv/bin/ragc" --store "$VERIFY_STORE" "$@"
  else
    env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m ragc --store "$VERIFY_STORE" "$@"
  fi
}

log "安装依赖..."
if "$PIP" install -q -e ".[dev]"; then
  ok "pip install -e . (venv)"
else
  fail "pip install -e ."
fi

if run_cli --version >/dev/null 2>&1; then
  ok "ragc --version"
else
  fail "ragc --version"
fi

if run_cli --help >/dev/null 2>&1; then
  ok "ragc --help"
else
  fail "ragc --help"
fi

if run_cli chunk --demo --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='chunk'
assert d['data_source']=='demo'
assert d['count']>=1
"; then
  ok "chunk --demo"
else
  fail "chunk --demo"
fi

SYNC_JSON=$(run_cli sync --demo --format json 2>/dev/null || true)
if echo "$SYNC_JSON" | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='sync'
assert d['data_source']=='demo'
assert d['chunks']>=1
assert d.get('mock') is True
open('/tmp/ragc_verify_kb_id','w').write(str(d['knowledge_base_id']))
"; then
  ok "sync --demo"
else
  fail "sync --demo"
fi

KB_ID=$(cat /tmp/ragc_verify_kb_id 2>/dev/null || echo 1)

if run_cli query "$KB_ID" "GEO 可见性" --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='query'
assert d['hit_count']>=1
assert isinstance(d.get('hits'), list)
"; then
  ok "query hybrid/fallback"
else
  fail "query"
fi

if run_cli kb list --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='kb-list'
assert d['count']>=1
"; then
  ok "kb list"
else
  fail "kb list"
fi

if "$PYTHON" -m pytest -q "$ROOT/tests" >/dev/null 2>&1; then
  ok "pytest"
else
  fail "pytest"
fi

rm -f "$VERIFY_STORE" /tmp/ragc_verify_kb_id
log "结果: PASS=$PASS FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]
