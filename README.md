# GEOFlow

> **v3 已为主开发线** · Laravel v2 保留在 [`v2-lts`](https://github.com/ExpeQiu/GEOflow/tree/v2-lts) 分支

面向 GEO（生成式引擎优化）的开源智能内容工程平台。

## 快速开始（v3）

```bash
cd geoflow-v3
cp .env.example .env
./scripts/start-local.sh      # 本地快速启动（推荐，无需 pgvector 镜像）
./scripts/verify-services.sh  # 服务验收
# 或 Docker 全栈（需能拉取 pgvector 镜像）：
./scripts/start.sh
./scripts/verify.sh
```

| 服务 | 默认地址 |
|------|----------|
| FastAPI | http://127.0.0.1:18081/health |
| geoflow-admin | http://127.0.0.1:13001/login |
| Flower | http://127.0.0.1:15555 |

默认账号：`admin` / `password`

## 仓库结构

```
GEOFlow/
├── geoflow-v3/          # v3 主栈（FastAPI + LangGraph + Next.js Admin）
├── guide/               # 现行指导（ADR、Runbook、集成）
│   └── archive/         # 过程日志与过期设计
├── docs/                # 多语言 README、分发文档
└── deploy-scripts/      # 部署脚本（仍含 Laravel v2，勿当 v3 生产路径）
```

仓内 `RAG-CLI` / `Sim-sandbox-CLI` / `content-LangGraph-CLI` 为**归档外挂**，主栈不安装、运行时不依赖。见 [cli-plugins.md](guide/cli-plugins.md)。

## 技术栈（v3）

| 层 | 技术 |
|----|------|
| 后台 | Next.js 16 · geoflow-admin |
| API | FastAPI · Celery · WebSocket |
| AI | LangGraph（内嵌）· pgvector RAG |
| 数据库 | PostgreSQL 16 + pgvector |
| 公网 Wiki | [GEOweb](/Volumes/Lexar/git/03T/GEOweb)（独立仓库，`/api/geoflow/sync` 契约） |

## Laravel v2（LTS 分支）

维护 bugfix 或回滚时切换到 `v2-lts` 分支：

```bash
git fetch origin v2-lts
git checkout v2-lts
cd legacy/laravel
cp .env.example .env   # 或恢复归档的 .env
./scripts/start.sh
```

详见 `v2-lts` 分支下的 [`legacy/laravel/README.md`](https://github.com/ExpeQiu/GEOflow/blob/v2-lts/legacy/laravel/README.md)。

## 文档

- [文档索引](guide/README.md)
- [v3 架构](geoflow-v3/guide/architecture.md)
- [v3 验证报告](geoflow-v3/guide/verification-report.md)
- [GEOweb 集成](guide/geoweb-integration.md)
- [CLI 归档外挂](guide/cli-plugins.md)

## License

Apache License 2.0 — 见 [LICENSE](LICENSE)
