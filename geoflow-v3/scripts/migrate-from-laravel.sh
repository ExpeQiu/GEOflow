#!/usr/bin/env bash
# 从 Laravel GEOFlow PostgreSQL 迁移业务数据到 v3
set -euo pipefail

LARAVEL_DB_URL="${LARAVEL_DB_URL:-postgresql://geo_user:geo_password@127.0.0.1:15432/geo_flow}"
V3_DB_URL="${V3_DB_URL:-postgresql://geo_user:geo_password@127.0.0.1:15433/geo_flow}"
DUMP="/tmp/geoflow_laravel_dump.sql"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

TABLES=(
  admins ai_models prompts categories authors
  knowledge_bases knowledge_chunks
  tasks task_runs articles
  distribution_channels article_distributions
  article_evaluations insight_templates tech_ip_assets
  api_idempotency_keys
)

log "导出 Laravel 业务表..."
TABLE_ARGS=""
for t in "${TABLES[@]}"; do
  TABLE_ARGS="$TABLE_ARGS -t $t"
done

pg_dump "$LARAVEL_DB_URL" --data-only $TABLE_ARGS --no-owner --no-acl -f "$DUMP" 2>/dev/null || {
  log "WARN: pg_dump 失败，尝试全库导出"
  pg_dump "$LARAVEL_DB_URL" --data-only --no-owner -f "$DUMP"
}

log "导入 v3 数据库..."
psql "$V3_DB_URL" -f "$DUMP" 2>&1 | tail -5

log "行数校验..."
for t in tasks articles knowledge_chunks tech_ip_assets; do
  C1=$(psql "$LARAVEL_DB_URL" -tAc "SELECT count(*) FROM $t" 2>/dev/null || echo 0)
  C2=$(psql "$V3_DB_URL" -tAc "SELECT count(*) FROM $t" 2>/dev/null || echo 0)
  log "  $t: laravel=$C1 v3=$C2"
done

log "迁移完成。请运行 ./scripts/verify.sh 验收。"
