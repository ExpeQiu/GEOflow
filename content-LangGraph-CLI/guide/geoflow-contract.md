# 与 GEOFlow 契约对照（外挂，零运行时耦合）

> GEOFlow **独立闭环**；本仓为 workflow 离线试跑 / YAML 门禁外挂。  
> 生产仍走内嵌 [`run_workflow_sync`](../../geoflow-v3/backend/app/ai/workflow_runner.py)。  
> 总览：[guide/cli-plugins.md](../../guide/cli-plugins.md)

## 1. Workflow 类型白名单

| type | GEOFlow | content-lg | 说明 |
|------|---------|------------|------|
| `content` | ✓ | ✓ | 起草 → 引用校验 → 修订 → finalize |
| `content_pipeline` | ✓ | ✓ | Chief-Deputy 编辑部 |
| `url_import` | ✓ | ✓ | 清洗 → 知识 → 关键词 → 标题 |
| `semantic_chunk` | ✓ | ✓ | LLM 规划 + 规则切块 |

**配置真源**：`geoflow-v3/backend/app/ai/config/workflows.yml`  
主栈门禁：`tests/test_workflows_yml_contract.py`；本仓保持拷贝对齐，禁止长期双写漂移。

## 2. Mock 输出字段（冻结）

| workflow | 关键字段 |
|----------|----------|
| content / content_pipeline | `content`, `title`, `citations`, `engine`, `trace.steps` |
| url_import | `summary`, `library_name`, `keywords`, `titles`, `knowledge_markdown`, `analysis_source`, `engine` |
| semantic_chunk | `chunks[].index`, `chunks[].content`, `engine` |

## 3. CLI Envelope（外挂层）

```json
{
  "module": "workflow-content",
  "version": "0.1.0",
  "data_source": "demo|mock|live",
  "fetched_at": "...",
  "workflow_type": "content",
  "result": { "...业务字段..." }
}
```

主栈 `run_workflow_sync` 不包此层；调用方自行剥皮。

## 4. 明确不做

- subprocess / pip 替换内嵌引擎
- CLI 充当生产 Sidecar
- `--task-id` 读 GEOFlow DB
- 将 mock 结果写入 TaskRun / Article
