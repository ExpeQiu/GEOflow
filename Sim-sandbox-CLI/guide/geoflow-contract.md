# 与 GEOFlow / PROBE-TRUTH 契约对照（外挂）

> 本仓独立演进；主栈已沉淀自有 `answer_parser`（parser_version=`v2`），**不** `import simsb`。  
> 总览：[guide/cli-plugins.md](../../guide/cli-plugins.md)

## metric_kind

| 值 | 含义 | 本仓 |
|----|------|------|
| `fixture` | 夹具评测 | `simsb eval` |
| `bias_report` | 偏移报告 | `simsb calibrate` |
| `open_api` | 生产 Open-API 指数 | 不实现（主工程） |
| `cend_sample` | C 端金标 | calibrate 的 gold 侧 |
| `llm_sim` | 受控生成答文 | 未做 |
| `corpus` | 语料匹配 | 不做为主轨 |

## ProbeOutcome / 解析字段对齐

| 字段 | GEOFlow 主栈 | 本仓 |
|------|-------------|------|
| `mentioned` | ✅ | ✅ |
| `brand_rank` | ✅ Rank v2 | ✅ Rank v2 |
| `ranking_score` | ✅ 1→6 … 6→1 | ✅ 同权重 |
| `rank_method` | ✅ 落库（迁移 013） | ✅ |
| `evidence_level` | ✅ | ✅ L0 / L1 |
| `match_type` | ✅ | ✅ |
| `parser_version` | ✅ `v2` | 仿真固定 fixture 报告 |

## 外挂用途

1. `simsb eval`：夹具门禁（可对照主栈 `tests/fixtures/probe_rank`）
2. `simsb calibrate`：月度 Open-API vs 金标偏移报告 — **只出建议，禁止覆盖 `visibility_open_api`，不驱动 lift**
3. 新算法先在本仓验绿，再**拷入**主栈 `answer_parser.py`

## 非目标

- Playwright 爬 C 端登录态
- 沙箱结果驱动 lift
- 静默 corpus 冒充 citation
