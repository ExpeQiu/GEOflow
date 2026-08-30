#!/usr/bin/env bash
# 将 GEOFlow Admin(:8098) + GEOweb(:8093) 部署到腾讯云。
# 不改 PM2 gweb/techstore、不改 5433 小程序库、不改 8095/8096 Nginx。
# 用法: DEPLOY_SSH_PASS=... ./deploy-stack/deploy-tencent.sh [--skip-build] [--no-nginx]
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib.sh
source "${STACK_ROOT}/_lib.sh"
require_dirs || exit 1

SSH_HOST="${DEPLOY_SSH_HOST:-root@111.230.58.40}"
SSH_PASS="${DEPLOY_SSH_PASS:-}"
REMOTE_GEOFLOW="/opt/geoflow"
REMOTE_ADMIN="/opt/geoflow-admin"
REMOTE_GEOWEB="/opt/geoweb"
REMOTE_DATA="/opt/geoflow-data"
PUBLIC_HOST="${DEPLOY_PUBLIC_HOST:-111.230.58.40}"
GEOWEB_PUBLIC="http://${PUBLIC_HOST}:8093"
GEOFLOW_PUBLIC="http://${PUBLIC_HOST}:8098"

SKIP_BUILD=false
DO_NGINX=true
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    --no-nginx) DO_NGINX=false ;;
    --nginx) DO_NGINX=true ;;
    --help|-h)
      echo "用法: DEPLOY_SSH_PASS=... $0 [--skip-build] [--no-nginx]"
      exit 0
      ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

if [[ -z "$SSH_PASS" ]]; then
  ssh_cmd() { ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$SSH_HOST" "$@"; }
  scp_cmd() { scp -o StrictHostKeyChecking=no "$@"; }
  rsync_rsh="ssh -o StrictHostKeyChecking=no"
else
  command -v sshpass >/dev/null || { err "需要 sshpass"; exit 1; }
  ssh_cmd() { sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$SSH_HOST" "$@"; }
  scp_cmd() { sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$@"; }
  rsync_rsh="sshpass -p ${SSH_PASS} ssh -o StrictHostKeyChecking=no"
fi

rsync_cmd() {
  COPYFILE_DISABLE=1 rsync -az --delete \
    --exclude '.env' --exclude 'logs/' --exclude 'storage/questions/' \
    -e "$rsync_rsh" "$@"
}

LOG_DIR="${STACK_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/deploy-tencent-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
log "===== deploy-tencent 开始 log=$LOG_FILE ====="

copy_prisma_engines() {
  local root="$1"
  local out="$2"
  mkdir -p "$out/node_modules"
  local prisma_src="$root/node_modules/.prisma"
  if [[ ! -d "$prisma_src" ]]; then
    prisma_src="$(find "$root/node_modules/.pnpm" -path "*/node_modules/.prisma" -type d 2>/dev/null | head -1 || true)"
  fi
  if [[ -z "$prisma_src" || ! -d "$prisma_src" ]]; then
    err "未找到 .prisma，请先在 GEOweb 执行 npx prisma generate"
    exit 1
  fi
  COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
    "$prisma_src/" "$out/node_modules/.prisma/"
  if [[ -d "$root/node_modules/@prisma" ]]; then
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
      "$root/node_modules/@prisma/" "$out/node_modules/@prisma/"
  fi
  if ! find "$out/node_modules/.prisma" -name 'libquery_engine-debian-openssl-1.0.x.so.node' 2>/dev/null | grep -q .; then
    err "Prisma 缺少 debian-openssl-1.0.x（OpenCloudOS 现网），对齐 Gweb binaryTargets 后重新 generate"
    exit 1
  fi
}

pack_standalone() {
  local root="$1"
  local out="$2"
  log "打包 standalone → $out"
  rm -rf "$out"
  mkdir -p "$out/.next"
  if [[ ! -f "$root/.next/standalone/server.js" ]]; then
    # Next 有时把 server.js 放在包名子目录
    local nested
    nested="$(find "$root/.next/standalone" -name server.js | head -1 || true)"
    if [[ -z "$nested" ]]; then
      err "未找到 standalone/server.js（先 npm run build）"
      exit 1
    fi
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
      "$(dirname "$nested")/" "$out/"
  else
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
      "$root/.next/standalone/" "$out/"
  fi
  if [[ -d "$root/.next/static" ]]; then
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
      "$root/.next/static/" "$out/.next/static/"
  fi
  if [[ -d "$root/public" ]]; then
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' --exclude='.DS_Store' \
      "$root/public/" "$out/public/"
  fi
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! $SKIP_BUILD; then
  log "构建 GEOweb"
  (
    cd "$GEOWEB_ROOT"
    if [[ ! -d node_modules/next ]]; then
      npm install --no-audit --no-fund
    fi
    export DATABASE_URL="${DATABASE_URL:-postgresql://build:build@127.0.0.1:5432/build?connect_timeout=1}"
    export TECHSTORE_PUBLIC_URL="http://127.0.0.1:3013"
    export NEXT_PUBLIC_SITE_URL="$GEOWEB_PUBLIC"
    export AI_MOCK_MODE=true
    export NEXT_TELEMETRY_DISABLED=1
    npx prisma generate
    npm run build
  )
  pack_standalone "$GEOWEB_ROOT" "$TMP_DIR/geoweb"
  copy_prisma_engines "$GEOWEB_ROOT" "$TMP_DIR/geoweb"
  mkdir -p "$TMP_DIR/geoweb/content/wiki" "$TMP_DIR/geoweb/storage/questions"
  if [[ -d "$GEOWEB_ROOT/content" ]]; then
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' "$GEOWEB_ROOT/content/" "$TMP_DIR/geoweb/content/"
  fi
  if [[ -d "$GEOWEB_ROOT/prisma" ]]; then
    COPYFILE_DISABLE=1 rsync -a --exclude='._*' "$GEOWEB_ROOT/prisma/" "$TMP_DIR/geoweb/prisma/"
  fi

  log "构建 geoflow-admin"
  (
    cd "$GEOFLOW_V3_ROOT/apps/geoflow-admin"
    if [[ ! -d node_modules/next ]]; then
      npm install --no-audit --no-fund
    fi
    export API_INTERNAL_URL="http://127.0.0.1:18081"
    export NEXT_PUBLIC_API_URL="http://127.0.0.1:18081"
    export NEXT_TELEMETRY_DISABLED=1
    npm run build
  )
  pack_standalone "$GEOFLOW_V3_ROOT/apps/geoflow-admin" "$TMP_DIR/admin"
else
  err "--skip-build 暂未实现本地产物缓存，请去掉该参数"
  exit 1
fi

log "同步到服务器"
ssh_cmd "mkdir -p $REMOTE_GEOFLOW/backend $REMOTE_GEOFLOW/logs $REMOTE_ADMIN $REMOTE_GEOWEB $REMOTE_DATA/postgres $REMOTE_DATA/redis /opt/geoflow-stack"

rsync_cmd \
  --exclude '__pycache__' --exclude '.venv' --exclude 'venv' --exclude '.pytest_cache' \
  --exclude 'storage/uploads/*' --exclude '._*' \
  "$GEOFLOW_V3_ROOT/backend/" "$SSH_HOST:$REMOTE_GEOFLOW/backend/"

rsync_cmd "$TMP_DIR/admin/" "$SSH_HOST:$REMOTE_ADMIN/"
rsync_cmd "$TMP_DIR/geoweb/" "$SSH_HOST:$REMOTE_GEOWEB/"

scp_cmd \
  "$STACK_ROOT/remote-bootstrap.sh" \
  "$GEOFLOW_ROOT/../Gweb/scripts/deploy/nginx-gweb-stack.conf" \
  "$SSH_HOST:/opt/geoflow-stack/"

log "远端 bootstrap"
ssh_cmd "chmod +x /opt/geoflow-stack/remote-bootstrap.sh && \
  GEOWEB_PUBLIC='$GEOWEB_PUBLIC' GEOFLOW_PUBLIC='$GEOFLOW_PUBLIC' \
  bash /opt/geoflow-stack/remote-bootstrap.sh"

if $DO_NGINX; then
  log "安装 Nginx gweb-stack（含 8093/8098，不拆独立 conf）"
  ssh_cmd bash -s <<'REMOTE'
set -euo pipefail
cp /opt/geoflow-stack/nginx-gweb-stack.conf /www/server/panel/vhost/nginx/gweb-stack.conf
rm -f /www/server/panel/vhost/nginx/geo-stack.conf
NGINX_BIN="/www/server/nginx/sbin/nginx"
[[ -x "$NGINX_BIN" ]] || NGINX_BIN="$(command -v nginx)"
"$NGINX_BIN" -t
if [[ -s /www/server/nginx/logs/nginx.pid ]] && kill -0 "$(cat /www/server/nginx/logs/nginx.pid)" 2>/dev/null; then
  "$NGINX_BIN" -s reload
else
  "$NGINX_BIN"
fi
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port=8093/tcp || true
  firewall-cmd --permanent --add-port=8098/tcp || true
  firewall-cmd --reload || true
fi
REMOTE
fi

log "等待健康检查"
sleep 8
ssh_cmd bash -s <<'REMOTE'
set -euo pipefail
echo "=== PM2 ==="
pm2 list | grep -E "gweb|techstore|geoflow|geoweb|name" || pm2 list
echo "=== 健康 ==="
curl -sf --max-time 8 http://127.0.0.1:18081/health && echo "" || { echo "API FAIL"; tail -40 /opt/geoflow/logs/api.err.log || true; }
curl -sI --max-time 8 http://127.0.0.1:3015/login | head -8 || echo "Admin FAIL"
curl -sI --max-time 8 http://127.0.0.1:3014/ | head -8 || echo "GEOweb FAIL"
curl -sf --max-time 8 http://127.0.0.1:3012/api/health && echo " (gweb still ok)" || echo "Gweb REGRESSION"
curl -sf --max-time 8 http://127.0.0.1:3013/api/health && echo " (techstore still ok)" || echo "Techstore REGRESSION"
echo "=== 内存 ==="
free -h | head -2
REMOTE

log "公网探测"
curl -sI --max-time 15 "http://${PUBLIC_HOST}:8093/" | head -8 || true
echo "---"
curl -sf --max-time 15 "http://${PUBLIC_HOST}:8098/health" && echo "" || true
curl -sf --max-time 10 "http://${PUBLIC_HOST}:8095/api/health" && echo " gweb 8095 still ok" || echo "WARN 8095"

log "完成"
echo "  GEOweb:   ${GEOWEB_PUBLIC}/"
echo "  GEOFlow:  ${GEOFLOW_PUBLIC}/login"
echo "  API:      ${GEOFLOW_PUBLIC}/health"
echo "  默认账密: admin / password （请立刻改密）"
echo "  日志:     $LOG_FILE"
echo "===== deploy-tencent 结束 ====="
