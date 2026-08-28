# 三仓 Docker 部署

一套 Postgres（`geo_flow` + `gweb_db`），一个网络 `geo-net`。可分仓部署，也可一键拉起。

## 端口

| 服务 | 地址 |
|------|------|
| Postgres | `127.0.0.1:15433` |
| Redis | `127.0.0.1:16380` |
| GEOFlow API | http://127.0.0.1:18081/health |
| GEOFlow Admin | http://127.0.0.1:13001/login |
| Techstore | http://127.0.0.1:3001/admin |
| GEOweb | http://127.0.0.1:3070/ |

## 一键

需三仓为兄弟目录：`03T/GEOFlow`、`03T/Techstore`、`03T/GEOweb`。路径不对时设 `TECHSTORE_ROOT` / `GEOWEB_ROOT`。

```bash
cd /Volumes/Lexar/git/03T/GEOFlow/deploy-stack
# 缺镜像时允许拉取
GEOFLOW_PULL=missing ./start.sh
./verify.sh
./stop.sh           # 停全部（含 Postgres）
./stop.sh --apps    # 只停应用，保留库
```

默认 `GEOFLOW_PULL=never`：本地没有 `pgvector/pgvector:pg16` 时会失败，改用 `GEOFLOW_PULL=missing`。

## 分别部署

```bash
# 1) 共享库（必须先有 geo-net + Postgres）
cd ../geoflow-v3 && ./scripts/start.sh infra

# 2a) 只跑 GEOFlow 全栈
./scripts/start.sh

# 2b) 只跑 Techstore
cd ../../Techstore && ./start.sh docker          # 已有 infra
./start.sh docker --with-infra                   # 顺带起 Postgres

# 2c) 只跑 GEOweb
cd ../../GEOweb && ./scripts/start.sh docker
./scripts/start.sh docker --with-infra
```

停止单仓（不停 Postgres）：

```bash
cd Techstore && ./stop.sh docker
cd GEOweb && ./scripts/stop.sh docker
```

停 GEOFlow `./scripts/stop.sh` 会停掉共享 Postgres，Techstore/GEOweb 会连不上库。

## 容器内主机名

| 名 | 用途 |
|----|------|
| `postgres` | 两库：`geo_flow` / `gweb_db` |
| `api` | GEOFlow FastAPI |
| `techstore` | 后台 :3000 |
| `geoweb` | 前台 :3000 |

浏览器仍走上表宿主机端口。GEOFlow 同步 GEOweb 在栈内用 `GEOWEB_BASE_URL=http://geoweb:3000`。

## 迁移

- `geo_flow`：GEOFlow start 跑 `alembic upgrade head`
- `gweb_db`：Techstore 容器入口 `prisma migrate deploy`
- GEOweb **不 migrate**
