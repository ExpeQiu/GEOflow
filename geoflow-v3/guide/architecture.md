# GEOFlow v3 架构说明

> Laravel v2 保留在 `v2-lts` 分支（`legacy/laravel/`）

## 栈

- **backend/** — FastAPI + SQLAlchemy + Celery + LangGraph（内嵌 content-agent）
- **apps/geoflow-admin/** — Next.js 16 独立管理后台
- **Gweb** — 公网 Wiki 展现（外部仓库，wiki/sync 契约不变）

## 启动

```bash
cp .env.example .env
./scripts/start.sh
./scripts/verify.sh
```

## 大爆炸切流

1. `./scripts/migrate-from-laravel.sh` 迁移数据
2. 反代切换 `/api/v1` → v3 API；Admin → geoflow-admin
3. Laravel 归档至 `v2-lts` 分支（`legacy/laravel/`）

## API

- REST: `/api/v1/*`（兼容 Laravel Sanctum scope）
- Admin BFF: `/api/admin/*`（JWT）
- WebSocket: `/ws/admin/tasks`
