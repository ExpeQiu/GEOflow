# GEOFlow v3 验证报告

> 更新：2026-07-03

## 升级计划完成项（Wave 0–4 + AIVIS A–D）

| Wave | 内容 | 状态 |
|------|------|------|
| Wave 0–4 | 基础闭环、分发、Materials | 完成 |
| **Wave A** | 007 migration、加权排名、国内 6 平台、模板/场景/竞品 | 完成 |
| **Wave B** | 场景缺口、Task 闭环、豆包/DeepSeek API | 完成 |
| **Wave C** | 情感分析、竞品矩阵、market-scan、洞察、告警 | 完成 |
| **Wave D** | 诊断报告 HTML、趋势快照、Monitor 多 Tab | 完成 |

## 本地验证

```bash
cd geoflow-v3 && ./scripts/start.sh
docker compose exec backend alembic upgrade head   # 至 007_aivis_foundation
./scripts/verify.sh
```

## AIVIS smoke 端点

- `GET /api/admin/strategy/monitor/scenes|templates|competitors|snapshots|insights|reports`
- `POST /api/admin/strategy/monitor/reports/generate`
- `POST /api/admin/strategy/monitor/scenes/{id}/create-task`

## 待 UAT（非阻塞）

- 通义/文心/Kimi/元宝 API Connector 全量 E2E
- LLM 探针 daily_limit 限流
- Admin 6 语言 i18n
- RAG 生产 embedding（缺口分析精度）
