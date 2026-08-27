# CLI 外挂契约（归档）

> 更新：2026-08-26  
> 状态：**归档外挂**。主栈不安装、生产不 `import` / 不起 CLI 子进程。  
> 原则：**不安装任何 15CLI，GEOFlow 闭环仍可运行、可验收。**  
> 经验证算法以主栈自有代码沉淀。本波冻结：不再为这三套 CLI 加功能。

---

## 外挂一览

| CLI | 角色 | 主栈生产路径 | 是否运行时依赖 |
|-----|------|--------------|----------------|
| **Sim-sandbox-CLI** | Rank/Citation 夹具评测 + 金标偏移 | 主栈 `answer_parser` + ApiConnector | 否（可选沉淀） |
| **RAG-CLI** | 离线 sync/query、算法对照 | Celery + pgvector + Admin rag-sandbox | 否 |
| **content-LangGraph-CLI** | workflow 离线试跑 / YAML 门禁 | 内嵌 `run_workflow_sync` | 否 |

分工：`semantic_chunk`（LLM 规划）↔ content-lg；规则切分 + embedding + sync ↔ ragc / 主栈 RAG。

---

## 冻结字段契约

### 1. RAG query envelope

```json
{
  "knowledge_base_id": 1,
  "knowledge_base_name": "...",
  "query": "...",
  "hits": [
    {"chunk_id": 1, "chunk_index": 0, "content": "...", "score": 0.8, "source": "hybrid"}
  ],
  "hit_count": 1
}
```

`source` ∈ `vector` | `keyword` | `hybrid` | `fallback`  
（CLI 可另包 `module` / `fetched_at` 外层，主栈 Admin 不强制。）

### 2. ProbeOutcome 扩展（解析 v2）

| 字段 | 类型 | 说明 |
|------|------|------|
| `mentioned` | bool | 目标品牌是否出现 |
| `brand_rank` | int\|null | 位次（列表序优先） |
| `ranking_score` | float | 1→6 … 6→1 |
| `rank_method` | str | `list_order` \| `first_mention` \| `unknown` |
| `evidence_level` | str | `L0` \| `L1`（API 答文无官方引用时） |
| `match_type` | str | `domain_wiki` \| `domain_official` \| `none` |
| `parser_version` | str | 当前 `v2`；旧数据可空 |

主 KPI：`visibility_open_api` **永不**被 `simsb calibrate` / 金标覆盖。

### 2.1 Admin「GEO标准」↔ Sim-sandbox `calibration.yml`

配置面：`/production/geo-eval`（Track B 探针标准），持久化 `site_settings`（`group_name=probe_standards`）。  
生产路径**不**调用 `simsb`；旋钮语义对齐外挂 YAML。

| Admin / site_settings | calibration.yml | 说明 |
|----------------------|-----------------|------|
| `probe_metric_primary`（固定 open_api） | `metric_policy.primary` | 主口径不可改金标 |
| `probe_footnote_on_bias` | `metric_policy.footnote_on_bias` | KPI/报告脚注 |
| `probe_do_not_overwrite_open_api_kpi`（强制 true） | `metric_policy.do_not_overwrite_open_api_kpi` | 保存 false → 400 |
| `probe_rank_report_weight` | `rank.report_weight` | list_order / first_mention / unknown |
| `probe_min_evidence_level` | `citation.min_evidence_level_for_chain` | L0 / L1 |
| `probe_forbid_corpus_as_l1` | `citation.forbid_corpus_as_l1` | corpus 不得冒充 L1 |
| `probe_fixture_min_list_acc` | `simsb eval --min-list-acc`（默认 0.8） | 夹具门禁门槛展示 |
| `probe_scan_platforms` / `probe_priority_floor_daily` | `scan.*` | 扫描护栏草案 |

内容门禁（Track A）独立：`geo_eval_*` keys，见 `geo_eval_settings_service`。

### 3. Workflow 类型白名单

`content` | `content_pipeline` | `url_import` | `semantic_chunk`  
配置真源：`geoflow-v3/backend/app/ai/config/workflows.yml`。

---

## 验收（外挂可选）

1. 不启动 `ragc` / `simsb` / `content-lg`，按 [真实闭环P0](./archive/历史指导/真实闭环P0.md) 仍可完成探针→缺口→发布→lift。
2. 主栈单元测试覆盖 Rank v2 夹具（`tests/fixtures/probe_rank`）。
3. 外挂侧 `./start.sh`（等价 `./verify.sh`）可选跑，失败不阻断主栈部署。

## 禁止

- Celery / HTTP 主路径硬依赖 CLI
- CLI 直连主库写闭环表
- 外挂结果驱动 remediation lift 或改写 `visibility_open_api`

## 相关

- [真实闭环P0](./archive/历史指导/真实闭环P0.md)
- [探针真值标定](./探针真值标定专题.md)（标定外挂运营）
- [langgraph-orchestration](./langgraph-orchestration.md)
