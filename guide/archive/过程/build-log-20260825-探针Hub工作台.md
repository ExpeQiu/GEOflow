# 构建日志 · 探针 Hub 四套 scheme 工作台

- 日期：2026-08-25
- 对照：ADR-012 · `guide/探针设计.md` §8.1

## 做了什么

1. `ProbesHub` 五 tab：采集工作台 / 问题库 / 交叉判定 / 金标对照 / 探针设置；`?view=` 读写同步。
2. `/strategy/gold-labels` 跳转 `?view=gold`；策略「更多」去掉金标项。
3. 采集 API 返回 `scheme_cards[]` + `recent_runs.scheme`（由 `geo_monitor_runs.platform` 前缀推导，不新开表）。
4. 采集页改为四套 scheme 卡片，扫描互斥；辅轨文案标明不覆盖北极星。
5. 诊断页「探针设置」链到 `?view=settings`。
6. Hub A/B 辅轨扫描改读 `probe_settings.platforms`（当前 deepseek），去掉写死的 doubao/kimi。

## 验证

```
cd geoflow-v3/backend && .venv/bin/python -m pytest tests/test_probe_scheme.py -q
```
