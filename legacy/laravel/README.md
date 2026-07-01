# GEOFlow v2（Laravel LTS 归档）

> 2026-07 大爆炸迁移后归档。新功能开发请使用 [`../../geoflow-v3/`](../../geoflow-v3/)。

## 栈

- PHP 8.2+ · Laravel 12
- PostgreSQL + pgvector · Redis · Horizon
- Blade 后台 · 可选 Python Content Agent 侧车
- Docker Compose

## 启动（回滚 / 维护）

```bash
cd legacy/laravel
cp .env.example .env    # 或使用已归档的 .env
./scripts/start.sh
./scripts/verify.sh
```

| 服务 | 默认 |
|------|------|
| 后台 | http://127.0.0.1:18080/geo_admin |
| API | http://127.0.0.1:18080/api/v1 |

## 目录说明

| 路径 | 说明 |
|------|------|
| `app/` | Laravel 业务层（GeoFlow / GeoEval） |
| `services/content-agent/` | LangGraph Python 侧车（v3 已内嵌至 FastAPI） |
| `database/migrations/` | 38 个 migration |
| `resources/views/admin/` | Blade 后台（149 视图） |
| `scripts/` | start · stop · verify |

## 与 v3 数据迁移

从本目录运行的 Laravel 数据库导出至 v3：

```bash
LARAVEL_DB_URL=postgresql://geo_user:geo_password@127.0.0.1:15432/geo_flow \
V3_DB_URL=postgresql://geo_user:geo_password@127.0.0.1:15433/geo_flow \
../../geoflow-v3/scripts/migrate-from-laravel.sh
```

## Git 标签建议

归档时可打：`git tag v2-lts -m "Laravel stack archived"`
