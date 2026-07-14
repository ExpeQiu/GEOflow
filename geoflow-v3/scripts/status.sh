#!/usr/bin/env bash
# 本地栈状态一览（进程 / 端口 / 数据指纹 / 日志路径）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"

ok() { printf '  %-10s %s\n' "$1" "$2"; }

echo "=== GEOFlow v3 status ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# Redis
if redis_ok; then ok Redis UP; else ok Redis DOWN; fi

# Postgres
if docker ps --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  VOL="$(docker inspect "${PG_NAME}" --format '{{range .Mounts}}{{.Name}}{{end}}' 2>/dev/null || true)"
  ok Postgres "UP (:${PG_PORT}) vol=${VOL:0:20}..."
  ARTICLES="$(docker exec "${PG_NAME}" psql -U geo_user -d geo_flow -tAc 'SELECT count(*) FROM articles' 2>/dev/null || echo '?')"
  SCENES="$(docker exec "${PG_NAME}" psql -U geo_user -d geo_flow -tAc 'SELECT count(*) FROM geo_monitor_scenes' 2>/dev/null || echo '?')"
  VER="$(docker exec "${PG_NAME}" psql -U geo_user -d geo_flow -tAc 'SELECT version_num FROM alembic_version' 2>/dev/null || echo '?')"
  ok Data "articles=${ARTICLES} scenes=${SCENES} alembic=${VER}"
elif docker ps -a --format '{{.Names}}' | grep -q "^${PG_NAME}$"; then
  ok Postgres "STOPPED (容器保留，数据应仍在 volume)"
else
  ok Postgres "MISSING"
fi

# API
if wait_http_ok "http://127.0.0.1:${API_PORT}/health" 1 "ok"; then
  PID="?"
  pid_alive "${GEOFLOW_API_PID}" && PID="$(tr -d '[:space:]' <"${GEOFLOW_API_PID}")"
  ok API "UP (:${API_PORT}) watchdog=${PID}"
else
  ok API "DOWN (:${API_PORT})"
fi

# Admin
if wait_http_ok "http://127.0.0.1:${ADMIN_PORT}/login" 1; then
  PID="?"
  pid_alive "${GEOFLOW_ADMIN_PID}" && PID="$(tr -d '[:space:]' <"${GEOFLOW_ADMIN_PID}")"
  ok Admin "UP (:${ADMIN_PORT}) watchdog=${PID}"
else
  ok Admin "DOWN (:${ADMIN_PORT})"
fi

echo "日志:"
ok api "${GEOFLOW_API_LOG}"
ok admin "${GEOFLOW_ADMIN_LOG}"
ok start "${GEOFLOW_START_LOG}"
echo "入口: http://127.0.0.1:${ADMIN_PORT}/login"
