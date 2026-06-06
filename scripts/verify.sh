#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:-docker}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ "$MODE" = "docker" ]; then
  log "Docker 运行态检查"
  docker compose ps
  APP_PORT="${APP_PORT:-18080}"
  if curl -sf "http://127.0.0.1:${APP_PORT}/" >/dev/null; then
    log "GEOworkflow 前台 OK (:${APP_PORT})"
  else
    log "WARN: GEOworkflow 前台未响应"
  fi
  if docker compose exec -T app php artisan migrate:status --no-ansi 2>/dev/null | grep -q geo_eval; then
    log "geo_eval 迁移已登记"
  else
    docker compose exec -T app php artisan migrate:status --no-ansi 2>/dev/null | tail -5 || true
  fi
  if docker compose exec -T app php artisan tinker --execute="echo config('geo_eval.enabled') ? 'geo_eval_on' : 'geo_eval_off';" 2>/dev/null | grep -q geo_eval_on; then
    log "GEO 策略模块已启用（内置引擎）"
  else
    log "GEO 策略模块未启用（GEO_EVAL_ENABLED=false）"
  fi
  exit 0
fi

if [ "$MODE" = "geo-alert-dry-run" ]; then
  docker compose exec -T app php artisan geo:check-adoption-alerts 2>&1 || true
  exit 0
fi

if [ "$MODE" = "geo-eval" ]; then
  if docker compose exec -T app ./vendor/bin/phpunit --filter=GeoEval 2>/dev/null; then
    exit 0
  fi
  log "容器内 PHPUnit 不可用，尝试宿主机"
fi

if [ "$MODE" = "content-agent" ]; then
  log "Content Agent 可插拔链路检查"
  if docker compose ps --status running 2>/dev/null | grep -q content-agent; then
    if docker compose exec -T content-agent wget -q -O - http://127.0.0.1:8000/v1/health 2>/dev/null | grep -q '"ok"'; then
      log "content-agent health OK"
    else
      log "WARN: content-agent health 未响应"
    fi
  else
    log "content-agent 容器未运行（backend=internal 时可忽略）"
  fi
  if docker compose exec -T app php artisan migrate:status --no-ansi 2>/dev/null | grep -q content_agent_requests; then
    log "content_agent_requests 迁移已登记"
  else
    log "WARN: content_agent_requests 迁移未找到"
  fi
  BACKEND="$(docker compose exec -T app php artisan tinker --execute="echo config('geoflow.content_agent.backend');" 2>/dev/null | tail -1 || true)"
  log "GEOFLOW_CONTENT_AGENT_BACKEND=${BACKEND:-unknown}"
  if docker compose exec -T app php artisan test --filter=ContentAgent 2>/dev/null; then
    log "ContentAgent PHPUnit OK"
  else
    log "WARN: ContentAgent 测试未通过或 PHPUnit 不可用"
  fi
  exit 0
fi

if [ -f vendor/bin/phpunit ]; then
  ./vendor/bin/phpunit --filter=GeoEval
elif command -v php >/dev/null 2>&1; then
  php artisan test --filter=GeoEval
else
  log "跳过 PHPUnit（无 php/vendor）"
fi

log "验证完成"
