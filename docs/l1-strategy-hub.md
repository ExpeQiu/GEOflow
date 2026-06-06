# L1 效果与策略 Hub

统一入口：`/geo_admin/strategy`（路由名 `admin.strategy.index`）

## 模块

| Tab | 能力 | 服务 |
|-----|------|------|
| 总览 | KPI、告警摘要 | `StrategyHubController` |
| 监控问题库 | 批量导入、技术关键词、多 AI 平台探测、可视化看板 | `MonitorQuestionService`, `MonitorAiProbeService`, `MonitorDashboardService` |
| 外部信源 | URL 注册、对比报告、InsightTemplate | `WebSourceRegistry`, `StrategyInsightComposer` |
| 仿真与建议 | 评估诊断、优化建议、一键应用草稿 | `ArticleEvaluationService`, `OptimizationAdvisorService` |
| 采纳分析 | 采纳率趋势（自 analytics 区块迁入） | `GeoEvalAnalyticsService` |

## 数据表

- `geo_monitor_questions` / `geo_monitor_runs` / `geo_monitor_results`
- `geo_monitor_platform_configs` / `geo_monitor_ai_probe_results`
- 站点设置 `geo_monitor_tech_keywords`（技术关键词/品牌词）
- `geo_web_sources` / `geo_web_insight_reports`

## Artisan 命令

```bash
php artisan geo:monitor-scan --type=daily
php artisan geo:monitor-scan --async
php artisan geo:web-intel-refresh
php artisan geo:web-intel-refresh --async
php artisan geo:check-adoption-alerts   # 含 rank_drop / accuracy_below_floor
```

## 调度（routes/console.php）

- `geo:monitor-scan` 每日 04:00
- `geo:web-intel-refresh --async` 每周二 05:00

## 配置（config/geo_eval.php）

- `monitor.scan_batch_size` / `rank_drop_threshold` / `accuracy_floor`
- `web_intel.refresh_days` / `max_sources_per_question`
- `advisor.llm_enhance`
- `simulation.llm_provider`：`mock`（默认）或真实 LLM

## 队列

- `RunMonitorScanJob` → `geo_eval`
- `RefreshWebSourceJob` → `geo_eval`

## 告警类型

- `low_adoption_rate` / `low_first_position_rate`（原有）
- `rank_drop` / `accuracy_below_floor`（监控库）
