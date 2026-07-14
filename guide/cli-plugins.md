# CLI 外挂契约（GEOFlow 独立闭环）

> 更新：2026-07-14  
> 原则：**不安装任何 15CLI，GEOFlow 闭环仍可运行、可验收。**  
> 外部 CLI 仅为能力增强外挂；经验证算法以主栈自有代码沉淀，生产不 `import` / 不起 CLI 子进程。

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

### 3. Workflow 类型白名单

`content` | `content_pipeline` | `url_import` | `semantic_chunk`  
配置真源：`geoflow-v3/backend/app/ai/config/workflows.yml`。

---

## 验收（外挂可选）

1. 不启动 `ragc` / `simsb` / `content-lg`，按 [真实闭环P0](./真实闭环P0.md) 仍可完成探针→缺口→发布→lift。
2. 主栈单元测试覆盖 Rank v2 夹具（`tests/fixtures/probe_rank`）。
3. 外挂侧各自 `./verify.sh` 可选跑，用于演进与对照，失败不阻断主栈部署。

## 禁止

- Celery / HTTP 主路径硬依赖 CLI
- CLI 直连主库写闭环表
- 外挂结果驱动 remediation lift 或改写 `visibility_open_api`

## 相关

- [真实闭环P0](./真实闭环P0.md)
- [探针真值标定](./探针真值标定专题.md)（标定外挂运营）
- [langgraph-orchestration](./langgraph-orchestration.md)
