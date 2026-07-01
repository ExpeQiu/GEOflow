#!/usr/bin/env bash
# [已废弃] 大爆炸切流已完成；Laravel v2 见 v2-lts 分支 legacy/laravel/
# 将 Laravel v2 代码归档至 legacy/laravel/（大爆炸切流后执行）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="${ROOT}/legacy/laravel"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

if [ -d "${ARCHIVE}/app" ]; then
  log "已归档，跳过（${ARCHIVE}/app 已存在）"
  exit 0
fi

log "开始归档 Laravel v2 → legacy/laravel/"

# Laravel 应用目录与配置
ITEMS=(
  app artisan bootstrap config database docker lang public resources routes
  services storage tests scripts
  composer.json composer.lock package.json package-lock.json
  phpunit.xml vite.config.js boost.json version.json opencode.json
  ecosystem.config.cjs
  docker-compose.yml docker-compose.prod.yml docker-compose.tencent.yml
  .env.example .env.prod.example .env.tencent
)

mkdir -p "${ARCHIVE}"

for item in "${ITEMS[@]}"; do
  if [ -e "${ROOT}/${item}" ]; then
    log "  mv ${item}"
    mv "${ROOT}/${item}" "${ARCHIVE}/"
  fi
done

# 运行时目录（若存在）
for item in vendor node_modules docker-data; do
  if [ -e "${ROOT}/${item}" ]; then
    log "  mv ${item} (runtime)"
    mv "${ROOT}/${item}" "${ARCHIVE}/" 2>/dev/null || true
  fi
done

# 用户 .env 随 Laravel 归档（便于 v2 回滚）
if [ -f "${ROOT}/.env" ]; then
  log "  mv .env → legacy/laravel/"
  mv "${ROOT}/.env" "${ARCHIVE}/.env"
fi

log "归档完成。v3 入口: geoflow-v3/"
