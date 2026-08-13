# GEOFlow v3 验证报告

> 更新：2026-08-13

## 升级计划完成项（Wave 0–4 + AIVIS A–D + 北极星 KPI）

| Wave | 内容 | 状态 |
|------|------|------|
| Wave 0–4 | 基础闭环、分发、Materials | 完成 |
| **Wave A–D** | AIVIS 场景/缺口/报告 | 完成 |
| **P0 真实闭环** | strict API、remediation lift、Gweb 对齐 | 完成 |
| **北极星 KPI（总览对齐）** | Top3/pp、质量灯、信源章、销售口径 API、014 迁移 | 完成 |

## 本地验证

```bash
cd geoflow-v3 && ./scripts/start.sh
# 无 Docker：GEOFLOW_NO_DOCKER=1 ./scripts/start-all.sh
cd backend && .venv/bin/alembic upgrade head   # 至 015_probe_gold_labels
.venv/bin/pip install -q pytest pytest-asyncio
.venv/bin/python -m pytest tests/test_north_star_kpi.py tests/test_answer_parser.py tests/test_probe_quota.py -q
```

## AIVIS / 北极星 smoke 端点

- `GET /api/admin/strategy/diagnosis` → `monitor.top3_pct` / `gap_vs_leader_top3_pp` / `quality` / `source`
- `GET /api/admin/strategy/overview`
- `POST /api/admin/strategy/monitor/reports/generate` → sections: overview/brand/quality/source/closed_loop（含金标脚注）
- `GET /api/admin/strategy/sales-copy` · `POST /api/admin/strategy/sales-copy`
- `GET /api/admin/strategy/geo-eval/articles/{id}`
- `GET /api/admin/strategy/gold-labels` · `GET …/gold-labels/bias` · `POST …/gold-labels`

## 待 UAT（非阻塞）

- 通义/文心/Kimi/元宝 API Connector 全量 E2E（需各平台 Key）
- Admin 6 语言 i18n
- 生产 Embedding 关闭 Mock 后全库重嵌
- 在真实 `ai_models.daily_limit` 打满后观察 skipped 占比（本地单测已覆盖配额逻辑）
