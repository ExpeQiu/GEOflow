# GEOFlow v3

全量迁移栈：**FastAPI + PostgreSQL/pgvector + LangGraph（内嵌）+ Celery + Next.js Admin**

Laravel v2 保留在仓库 `v2-lts` 分支（`legacy/laravel/`）；主开发线仅含 v3。

## 快速开始

本地推荐（复用本机 Redis + Postgres，守护进程防 IDE 杀软）：

```bash
cd geoflow-v3
cp .env.example .env
# 无 Docker：本机 Homebrew Postgres(:5432) + Redis
GEOFLOW_NO_DOCKER=1 ./scripts/start-all.sh
# 或 Docker 仅跑 Postgres 容器（需本地有 postgres:16-alpine）
./scripts/start-all.sh
./scripts/status.sh
./scripts/stop.sh
```

全量 Docker Compose（默认 `--pull never`，缺镜像会明确失败）：

```bash
./scripts/start.sh
./scripts/verify.sh
# 允许拉取: GEOFLOW_PULL=missing ./scripts/start.sh
```

| 服务 | 地址 |
|------|------|
| API | http://127.0.0.1:18081 |
| Admin | http://127.0.0.1:13001/login |
| Flower | http://127.0.0.1:15555 |

默认账号：`admin` / `password`

## 目录

```
geoflow-v3/
├── backend/           FastAPI 业务 + AI + Celery
├── apps/geoflow-admin Next.js 16 管理后台
├── scripts/           start · stop · verify · migrate-from-laravel
└── guide/             架构文档
```

## 从 Laravel 迁移

```bash
LARAVEL_DB_URL=postgresql://geo_user:geo_password@127.0.0.1:15432/geo_flow \
V3_DB_URL=postgresql://geo_user:geo_password@127.0.0.1:15433/geo_flow \
./scripts/migrate-from-laravel.sh
```

## GEOweb 集成

官方技术发布站为 [GEOweb](/Volumes/Lexar/git/03T/GEOweb)；通过 `GeowebPublisher` → `POST /api/geoflow/sync`（`channel_type=geoweb`）。  
**Gweb**（`08 Gene/Gweb`）是独立项目前台，不在 GEOFlow 分发链路。详见 `guide/geoweb-integration.md`。

存量 `gweb_wiki` 渠道清理：`scripts/migrate_gweb_channels_to_geoweb.py`。

## 开发

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8080
```

```bash
cd apps/geoflow-admin
npm install && npm run dev
```
