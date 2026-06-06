#!/usr/bin/env bash
# GEOFlow 腾讯云 PM2 部署
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

REMOTE_HOST="111.230.58.40"
REMOTE_USER="root"
REMOTE_PASS="Qb89100820"
REMOTE_DIR="/opt/geoflow"
WEB_PORT=3033
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=20"

_run_ssh() { sshpass -p "$REMOTE_PASS" ssh $SSH_OPTS "$REMOTE_USER@$REMOTE_HOST" "$1"; }
_run_scp() { sshpass -p "$REMOTE_PASS" scp $SSH_OPTS "$1" "$REMOTE_USER@$REMOTE_HOST:$2"; }

log() { echo "[$(date '+%H:%M:%S')] deploy $*"; }

if ! command -v sshpass &>/dev/null; then
  log "请安装 sshpass: brew install hudochenkov/sshpass/sshpass"
  exit 1
fi

log "1/6 本地构建前端资源..."
find . -name '._*' -delete 2>/dev/null || true
if [ -n "${DEPLOY_TENCENT_SKIP_BUILD:-}" ] && [ -f public/build/manifest.json ]; then
  log "  跳过（DEPLOY_TENCENT_SKIP_BUILD=1 且已有 public/build）"
elif [ -f package.json ]; then
  NPM_CACHE="${NPM_CACHE:-/tmp/npm-cache-geoflow}"
  npm install --cache "$NPM_CACHE" --silent 2>/dev/null || npm install --cache "$NPM_CACHE"
  npm run build
fi

log "2/6 打包项目..."
TARBALL="/tmp/geoflow-deploy.tar.gz"
[ "$(uname -s)" = "Darwin" ] && export COPYFILE_DISABLE=1
tar czf "$TARBALL" -C "$PROJECT_ROOT" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='vendor' \
  --exclude='storage/logs/*' \
  --exclude='storage/framework/cache/data/*' \
  --exclude='storage/framework/sessions/*' \
  --exclude='storage/framework/views/*' \
  --exclude='docker-data' \
  --exclude='.env' \
  --exclude='.phpunit.result.cache' \
  --exclude='._*' \
  .

log "  包体: $(ls -lh "$TARBALL" | awk '{print $5}')"

log "3/6 上传..."
_run_scp "$TARBALL" "/tmp/geoflow-deploy.tar.gz"
_run_ssh "mkdir -p ${REMOTE_DIR}/logs ${REMOTE_DIR}/docker-data/tencent/postgres ${REMOTE_DIR}/storage"
_run_ssh "tar xzf /tmp/geoflow-deploy.tar.gz -C ${REMOTE_DIR} && rm -f /tmp/geoflow-deploy.tar.gz"
rm -f "$TARBALL"

log "4/6 配置环境并启动数据库..."
_run_ssh "set -e
cd ${REMOTE_DIR}
cp -f .env.tencent .env 2>/dev/null || true
chmod +x scripts/pm2-artisan.sh scripts/deploy_tencent.sh 2>/dev/null || true
docker compose -f docker-compose.tencent.yml up -d
sleep 8
docker build -f docker/Dockerfile.cli.pm2 -t geoflow-php-cli:8.4 .
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan key:generate --force 2>/dev/null || true
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan migrate --force
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan db:seed --force
mkdir -p storage/framework/{cache/data,sessions,views} bootstrap/cache
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan config:cache
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan route:cache
docker run --rm --network host -v ${REMOTE_DIR}:/app -w /app --env-file ${REMOTE_DIR}/.env geoflow-php-cli:8.4 php artisan view:cache || true
chmod -R 775 storage bootstrap/cache 2>/dev/null || true
"

log "5/6 启动 PM2..."
_run_ssh "set -e
cd ${REMOTE_DIR}
chmod +x scripts/pm2-artisan.sh
pm2 delete geoflow-web geoflow-queue geoflow-scheduler geoflow-reverb 2>/dev/null || true
pm2 start ecosystem.config.cjs
pm2 save
"

log "6/6 验证..."
sleep 5
HTTP_CODE=$(_run_ssh "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${WEB_PORT}/ || echo 000")
log "HTTP ${HTTP_CODE} @ http://${REMOTE_HOST}:${WEB_PORT}/"
log "后台: http://${REMOTE_HOST}:${WEB_PORT}/geo_admin/login"
log "管理员: admin / Geoflow@2026!"
log "完成。"
