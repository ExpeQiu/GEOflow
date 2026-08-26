# GEOFlow 切流 Runbook（Wave 10）

> 更新：2026-08-13 · 对齐总览后台交付

## 前置

1. `alembic upgrade head`（至少至 `014_kpi_north_star`）
2. 生产 `.env`：`AI_MOCK_MODE=false`、`monitor_probe_mode=api`、`monitor_strict_api=true`
3. Embedding / Chat 模型 Key 已配；豆包/DeepSeek 探针可用
4. GEOweb `geoflow/sync` 契约联调通过；`official_domains` 已写入 site_settings

## 切流步骤

1. `./scripts/migrate-from-laravel.sh`（如有 v2 数据）→ 抽样校验 materials/articles/tasks
2. `./scripts/verify.sh` 全绿；额外 smoke：
   - `GET /api/admin/strategy/diagnosis` 返回 `monitor.top3_pct` / `gap_vs_leader_top3_pp`
   - `POST /api/admin/strategy/monitor/reports/generate` 报告含 `quality` / `source` 章
3. 反代：`/api/v1` → v3 FastAPI；Admin → geoflow-admin `:13001`
4. 写操作带 `Idempotency-Key`（materials / 关键发布）
5. Laravel 只读归档至 `v2-lts`

## 回滚

1. 反代切回 Laravel
2. 保留 v3 DB 不停机；停止新写入即可
3. 记录 `run_id` / 最近 remediation id 便于复盘

## 验收清单

- [ ] 北极星四卡可展示（允许空样本为 —）
- [ ] 参数一致率有 SSOT 时点亮门禁
- [ ] GEOweb 分发成功 → remediation awaiting_rescan → ΔTop3
- [ ] Embedding `ensure_production_ready` 在 Mock 关闭时 ready=true
- [ ] 关 Mock 后跑 `python scripts/reindex_all_knowledge.py`（Mock 下脚本拒绝）

## Embedding 全库重嵌

1. `.env`：`AI_MOCK_MODE=false`；Admin 至少一个 active embedding 模型
2. 重启 API + Celery Worker
3. `GET /api/admin/knowledge-bases/embedding-ready` → `ready=true, mode=api`
4. `python scripts/reindex_all_knowledge.py` 或知识库「全库重嵌」
5. 抽查 RAG sandbox 命中新向量

