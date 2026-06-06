# GEO 策略模块（GEOFlow 内置）

GEOFlow 为**完整独立项目**，不依赖 GEO-OS HTTP。能力设计参考 GEO-OS（`ARCHITECTURE.md`：strategy → simulate → verify → summary），在 Laravel 内实现。

## 代码位置

| 能力 | GEO-OS 参考 | GEOFlow 实现 |
|------|-------------|--------------|
| 仿真 + 审计 | `simulation/rag_sandbox`, `simulation/auditor` | `ArticleEvaluationService` + `InternalGeoEvalEngine` |
| URL 洞察 | `insight/strategy_miner` | `InsightTemplateService` |
| 采纳 / 趋势 | `api/routers/strategy` | `GeoEvalAnalyticsService` + `geo_strategy_metric_snapshots` |
| 发布门禁 | verify 节点 | `canPublish()` + `WorkerExecutionService` |
| 可观测 | `lib/trace`, event logs | `GeoEvalStructuredLogger`, `geo_eval_event_logs` |

引擎接口：`App\Services\GeoEval\Contracts\GeoEvalClientInterface`  
默认实现：`InternalGeoEvalEngine`（进程内，无出站 HTTP）。

## 环境变量

见 `.env.example` 中 `GEO_EVAL_*`（仅开关、门禁、仿真参数，无 `BASE_URL`）。

## 评估状态机

`pending_eval` → `passed` | `failed` | `skipped`

- `GEO_EVAL_GATE_ENABLED=true` 时，仅 `passed` / `skipped` 可自动发布。
- 异常时：`GEO_EVAL_ON_UNAVAILABLE=skip|block`。

## 演进路线（在 GEOFlow 内完成）

1. **P0**：内置仿真接知识库 + RAG 排名 + 规则审计（`InternalGeoEvalEngine`）。
2. **P1**：采纳指标从 `article_evaluations` / `geo_strategy_metric_snapshots` 聚合（已实现）。
3. **P1**：URL 挖掘接 HTTP 抓取 + LLM（对齐 StrategyMiner 规则）。
4. **P2**：`artisan schedule` 市场扫描 + 飞书/站内告警。
5. **L1 Hub**（已实现）：`/admin/strategy` 统一入口 — 监控问题库、外部信源、仿真建议、采纳分析。见 `docs/l1-strategy-hub.md`。

详细对照见 `docs/geo-strategy-architecture.md`。
