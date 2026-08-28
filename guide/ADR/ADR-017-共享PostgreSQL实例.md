# ADR-017：三仓共用一套 PostgreSQL 实例（两库）

- 状态：Accepted
- 日期：2026-08-28
- 相关：[ADR-014](./ADR-014-Techstore知识库导入.md)、GEOweb [ADR-003](/Volumes/Lexar/git/03T/GEOweb/ADR/ADR-003-PMS与素材只读接入.md)、[ADR-006](/Volumes/Lexar/git/03T/GEOweb/ADR/ADR-006-共享PostgreSQL实例.md)

## 决策

GEOFlow、Techstore、GEOweb **共用一台 Postgres**（镜像 `pgvector/pgvector:pg16`），**分成两个 database**，不合并 `public` schema、不合成业务表。

| Database | 迁移所有权 | 读写 |
|----------|------------|------|
| `geo_flow` | GEOFlow Alembic | GEOFlow 读写 |
| `gweb_db` | Techstore Prisma | Techstore 写；GEOweb 只读；GEOFlow 经 `TECHSTORE_DATABASE_URL` 只读导入 |

默认本地：`127.0.0.1:15433`，用户 `geo_user`。`pgvector` 扩展只装在 `geo_flow`。

## 非目标

- 把 `Domain` / `Technique` 与 `tech_ip_assets` 合成一张表（仍按 ADR-014）
- 让 Alembic 与 Prisma 共管同一 schema
- 把 Wiki MD / `storage/questions` 灌进 PG
- GEOweb 跑 `prisma migrate`

## 落地

- Compose：`docker/postgres-init/01-gweb_db.sql`（空卷首次）
- 幂等：`geoflow-v3/scripts/ensure-shared-databases.sh`（已有卷必跑）
- 启动：`start.sh` / `start-local.sh` 在 postgres ready 后调用 ensure
- 一键 Docker：[`deploy-stack/`](../../deploy-stack/README.md)

## 后果

- 整体部署只需一个 Postgres 容器、一份备份（`pg_dumpall` 或两库分别 dump）
- 迁移失败面隔离：Alembic 崩不影响 `gweb_db`，反之亦然
