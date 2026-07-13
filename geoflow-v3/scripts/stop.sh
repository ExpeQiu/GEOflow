#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-18081}"
ADMIN_PORT="${ADMIN_PORT:-13001}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "停止 Admin / API / Worker 本地进程..."
pkill -f "run-admin-watchdog.sh" 2>/dev/null || true
pkill -f "next dev.*--port ${ADMIN_PORT}" 2>/dev/null || true
pkill -f "run-api-watchdog.sh" 2>/dev/null || true
pkill -f "uvicorn app.main:app.*127.0.0.1:${API_PORT}" 2>/dev/null || true
pkill -f "run-worker-watchdog.sh" 2>/dev/null || true
pkill -f "celery -A app.workers.celery_app worker" 2>/dev/null || true
rm -f /tmp/geoflow-v3-admin.pid /tmp/geoflow-v3-api.pid /tmp/geoflow-v3-worker.pid

log "停止 PostgreSQL 容器..."
docker rm -f geoflow-v3-postgres-local 2>/dev/null || true

cd "$ROOT"
docker compose down 2>/dev/null || true
log "GEOFlow v3 已停止"
