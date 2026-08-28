# GEOFlow v3 架构说明

> Laravel v2 保留在 `v2-lts` 分支（`legacy/laravel/`）

## 栈

- **backend/** — FastAPI + SQLAlchemy + Celery + LangGraph（内嵌 content-agent）
- **apps/geoflow-admin/** — Next.js 16 独立管理后台
- **GEOweb** — 官方技术发布站（外部仓库，`/api/geoflow/sync`）

产品面收口见 [ADR-013](../guide/ADR/ADR-013-产品面收口与实验室分层.md)。仓内 RAG/Sim/content-lg CLI 为归档外挂，运行时不依赖。

## 启动

```bash
cp .env.example .env
./scripts/start.sh
./scripts/verify.sh
```

Postgres：同一实例两库 `geo_flow` + `gweb_db`，见 [ADR-017](../../guide/ADR/ADR-017-共享PostgreSQL实例.md)。启动后会跑 `scripts/ensure-shared-databases.sh`。

三仓 Docker（分仓或一键）：[deploy-stack](../../deploy-stack/README.md)。

## 大爆炸切流

1. `./scripts/migrate-from-laravel.sh` 迁移数据
2. 反代切换 `/api/v1` → v3 API；Admin → geoflow-admin
3. Laravel 归档至 `v2-lts` 分支（`legacy/laravel/`）

## API

- REST: `/api/v1/*`（兼容 Laravel Sanctum scope）
- Admin BFF: `/api/admin/*`（JWT）
- WebSocket: `/ws/admin/tasks`
