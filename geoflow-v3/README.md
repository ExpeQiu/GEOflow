# GEOFlow v3

全量迁移栈：**FastAPI + PostgreSQL/pgvector + LangGraph（内嵌）+ Celery + Next.js Admin**

Laravel v2 保留在仓库 `v2-lts` 分支（`legacy/laravel/`）；主开发线仅含 v3。

## 快速开始

```bash
cd geoflow-v3
cp .env.example .env
./scripts/start.sh    # Docker: postgres + redis + api + worker + admin
./scripts/verify.sh   # health + 登录验收
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

## Gweb 集成

Wiki 展现仍由 [Gweb](/Volumes/Lexar/git/08 Gene/Gweb) 负责；v3 通过 `GwebWikiPublisher` 调用 `POST /api/wiki/sync`，契约不变。

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
