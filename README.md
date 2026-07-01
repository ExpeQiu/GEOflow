# GEOFlow

> **v3 已为主开发线** · Laravel v2 已归档至 [`legacy/laravel/`](legacy/laravel/)

面向 GEO（生成式引擎优化）的开源智能内容工程平台。

## 快速开始（v3）

```bash
cd geoflow-v3
cp .env.example .env
./scripts/start.sh      # Docker 全栈
./scripts/verify-local.sh   # 本地结构 + pytest（无需 Docker）
./scripts/verify.sh     # Docker 运行态验收
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
├── legacy/laravel/      # v2 LTS 归档（Laravel 12 + Blade + Horizon）
├── guide/               # 架构与设计文档（含 v2 参考）
├── docs/                # 多语言 README、分发文档
└── deploy-scripts/      # 部署脚本
```

## 技术栈（v3）

| 层 | 技术 |
|----|------|
| 后台 | Next.js 16 · geoflow-admin |
| API | FastAPI · Celery · WebSocket |
| AI | LangGraph（内嵌）· pgvector RAG |
| 数据库 | PostgreSQL 16 + pgvector |
| 公网 Wiki | [Gweb](https://github.com/)（独立仓库，`wiki/sync` 契约） |

## Laravel v2（归档）

维护 bugfix 或回滚时使用：

```bash
cd legacy/laravel
cp .env.example .env   # 或恢复归档的 .env
./scripts/start.sh
```

详见 [`legacy/laravel/README.md`](legacy/laravel/README.md)。

## 文档

- [v3 架构](geoflow-v3/guide/architecture.md)
- [v3 验证报告](geoflow-v3/guide/verification-report.md)
- [v2 系统架构](guide/geoflow-architecture.html)
- [Gweb 集成](guide/gweb-integration.md)

## License

Apache License 2.0 — 见 [LICENSE](LICENSE)
