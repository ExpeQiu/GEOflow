#!/usr/bin/env bash
# PM2 通过 Docker PHP 镜像运行 artisan（宿主机 PHP 不可用时）
set -euo pipefail

ROOT="/opt/geoflow"
IMAGE="${GEOFLOW_PHP_IMAGE:-geoflow-php-cli:8.4}"
ENV_FILE="${ROOT}/.env"

exec docker run --rm \
  --network host \
  -v "${ROOT}:/app" \
  -w /app \
  --env-file "${ENV_FILE}" \
  "${IMAGE}" \
  php artisan "$@"
