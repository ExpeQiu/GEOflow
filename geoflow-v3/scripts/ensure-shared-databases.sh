#!/usr/bin/env bash
# 同一 Postgres 实例上确保 geo_flow + gweb_db。不跑 Alembic / Prisma。幂等。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/_common.sh
source "${ROOT}/scripts/_common.sh"

: "${PG_USER:=geo_user}"
: "${PG_PASSWORD:=geo_password}"
: "${PG_DB_FLOW:=geo_flow}"
: "${PG_DB_GWEB:=gweb_db}"

log "===== ensure-shared-databases 开始 port=${PG_PORT} ====="

db_exists() {
  local name="$1"
  local out
  out="$(run_psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${name}'" 2>/dev/null || true)"
  [[ "${out}" == *"1"* ]]
}

create_db() {
  local name="$1"
  local n=1
  log "CREATE DATABASE ${name} OWNER ${PG_USER}"
  while (( n <= 8 )); do
    if run_psql postgres -c "CREATE DATABASE ${name} OWNER ${PG_USER};"; then
      return 0
    fi
    log "CREATE DATABASE ${name} 重试 ${n}/8"
    n=$((n + 1))
    sleep 2
  done
  err "CREATE DATABASE ${name} 失败"
  return 1
}

detect_docker_pg() {
  local n
  for n in geoflow-v3-postgres "${PG_NAME}"; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "${n}"; then
      echo "${n}"
      return 0
    fi
  done
  return 1
}

run_psql() {
  local db="$1"
  shift
  case "${PG_MODE}" in
    docker)
      docker exec -e PGPASSWORD="${PG_PASSWORD}" "${PG_CONTAINER}" \
        psql -U "${PG_USER}" -d "${db}" "$@"
      ;;
    host)
      PGPASSWORD="${PG_PASSWORD}" psql -h 127.0.0.1 -p "${PG_PORT}" -U "${PG_USER}" -d "${db}" "$@"
      ;;
    *)
      err "未知 PG_MODE=${PG_MODE}"
      return 1
      ;;
  esac
}

PG_MODE=""
PG_CONTAINER=""
if command -v docker >/dev/null 2>&1 && PG_CONTAINER="$(detect_docker_pg)"; then
  PG_MODE="docker"
  log "探测到容器 ${PG_CONTAINER}"
  i=0
  until docker exec "${PG_CONTAINER}" pg_isready -U "${PG_USER}" -d postgres >/dev/null 2>&1; do
    i=$((i + 1))
    if (( i > 40 )); then
      err "容器内 postgres 未就绪"
      exit 1
    fi
    sleep 1
  done
  # 官方镜像首次 initdb 会先起临时进程再 shutdown；pg_isready 会误报就绪
  i=0
  until docker exec -e PGPASSWORD="${PG_PASSWORD}" "${PG_CONTAINER}" \
      psql -U "${PG_USER}" -d postgres -tAc "SELECT 1" >/dev/null 2>&1; do
    i=$((i + 1))
    if (( i > 60 )); then
      err "容器内 postgres 无法执行 SQL（可能仍在 initdb）"
      exit 1
    fi
    sleep 1
  done
elif command -v pg_isready >/dev/null 2>&1 && pg_isready -h 127.0.0.1 -p "${PG_PORT}" >/dev/null 2>&1; then
  PG_MODE="host"
  log "使用宿主机 Postgres :${PG_PORT}"
else
  err "未找到 Postgres。请先: cd geoflow-v3 && ./scripts/start.sh（或 start-local.sh）"
  exit 1
fi

for db in "${PG_DB_FLOW}" "${PG_DB_GWEB}"; do
  if db_exists "${db}"; then
    log "database ${db} 已存在"
  else
    create_db "${db}"
    log "database ${db} 已创建"
  fi
done

log "===== ensure-shared-databases 完成 mode=${PG_MODE} ====="
