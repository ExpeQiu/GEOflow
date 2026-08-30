# 2026-08-30 GEOFlow + GEOweb 腾讯云（共用 Gweb 栈）

- 入口：GEOweb `http://111.230.58.40:8093/` ；GEOFlow `http://111.230.58.40:8098/login`（health `/health`）
- 与 Gweb/Techstore 一致：PM2 + `gweb-stack.conf`（8095/8096/8093/8098）；Docker 仅 `backend-backend-1`、`backend-db-1`
- 库：`127.0.0.1:5433` 上 `gweb_db`（GEOweb 只读）+ `geo_flow`（GEOFlow，`SKIP_PGVECTOR=true`）
- 未起 Celery worker / 独立 Redis / 独立 Postgres
- 现网 Gweb `:8095`、Techstore `:8096` 健康未变
- Techstore 对接云上 GEOweb：`GEOWEB_URL=http://127.0.0.1:3014`，`GEOWEB_PUBLIC_URL=http://111.230.58.40:8093`；`POST /api/revalidate` 对 3014 返回 200；Gweb `GWEB_URL=3012` 仍保留
- 板块空数据：Prisma 缺 `debian-openssl-1.0.x`（OpenCloudOS）。补引擎后首页 25 图、地图/素材/FAQ 有数据；Gweb/Techstore 未动
