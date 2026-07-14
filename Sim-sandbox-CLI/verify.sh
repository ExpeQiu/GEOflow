#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PASS=0
FAIL=0

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
  if [[ -x "$ROOT/.venv/bin/simsb" ]]; then
    "$ROOT/.venv/bin/simsb" "$@"
  else
    env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m simsb "$@"
  fi
}

log "安装依赖..."
if "$PIP" install -q -e ".[dev]"; then
  ok "pip install -e . (venv)"
else
  fail "pip install -e ."
fi

if run_cli --version >/dev/null 2>&1; then
  ok "simsb --version"
else
  fail "simsb --version"
fi

if run_cli --help >/dev/null 2>&1; then
  ok "simsb --help"
else
  fail "simsb --help"
fi

if run_cli parse --brands 吉利 --competitors 比亚迪,小鹏 \
  --text $'1. 比亚迪\n2. 吉利\n3. 小鹏' --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='parse'
r=d['result']
assert r['mentioned'] is True
assert r['brand_rank']==2
assert r['rank_method']=='list_order'
assert r['evidence_level']=='L0'
"; then
  ok "parse list_order"
else
  fail "parse list_order"
fi

if run_cli eval --demo --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='eval'
assert d['data_source']=='demo'
assert d['metric_kind']=='fixture'
assert d['total']>=20
assert d['failed']==0
assert d.get('list_order_accuracy') is not None
assert d['list_order_accuracy']>=0.8
assert d.get('gate',{}).get('passed') is True
"; then
  ok "eval --demo gate"
else
  fail "eval --demo gate"
fi

if run_cli calibrate --demo --format json 2>/dev/null | "$PYTHON" -c "
import sys, json
d=json.load(sys.stdin)
assert d['module']=='calibrate'
assert d['paired']>=1
assert d['suggestions']['do_not_overwrite_open_api_kpi'] is True
"; then
  ok "calibrate --demo"
else
  fail "calibrate --demo"
fi

if "$PYTHON" -m pytest -q "$ROOT/tests" >/dev/null 2>&1; then
  ok "pytest"
else
  fail "pytest"
fi

log "结果: PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
