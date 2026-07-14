# 与 GEOFlow 契约对照（外挂，零运行时耦合）

> GEOFlow **独立闭环**；本仓为离线 RAG 作业外挂。生产 sync/query 仍走 Celery + pgvector + Admin rag-sandbox。  
> 总览：[guide/cli-plugins.md](../../guide/cli-plugins.md)

## 主链路对照

| GEOFlow | RAG-CLI | 状态 |
|---------|---------|------|
| `split_with_overlap` | `ragc.core.chunking` | 对齐（有意双份） |
| `EmbeddingService` mock sha256×12→3072 | `mock_embed` | 对齐 |
| `KnowledgeChunkSyncService` 删旧重建 | `ragc sync` | 语义对齐（本地 store） |
| `KnowledgeRetrievalService` hybrid | `ragc query` | 对齐合并公式 |
| Admin rag-sandbox 输出 hits | `query` envelope | 字段对齐 |
| Celery `sync_knowledge_chunks` | 进程内 sync | CLI 同步执行，无队列 |
| pgvector `<=>` | 内存余弦相似度 | 近似替代 |

## 输出契约（query）

```json
{
  "module": "query",
  "knowledge_base_id": 1,
  "knowledge_base_name": "...",
  "query": "...",
  "hits": [{"chunk_id", "chunk_index", "content", "score", "source"}],
  "hit_count": 1
}
```

`source` ∈ `vector` | `keyword` | `hybrid` | `fallback`

主栈冻结测试：`geoflow-v3/backend/tests/test_rag_chunking_contract.py`（不 import ragc）。

## 外挂用途

1. 本地试验切分 / 检索对照（运维增强）
2. `./verify.sh` 离线门禁
3. **禁止**：主栈 pip 依赖本仓；MCP 挂全库 rebuild 进生产热路径

与 content-LangGraph-CLI：`semantic_chunk` 归 content-lg；规则切分+embed+sync 归本仓。
