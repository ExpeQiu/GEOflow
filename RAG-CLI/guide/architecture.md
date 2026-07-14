# 架构说明

## 目标

独立验证 RAG / Embedding **生产作业** CLI，不修改 GEOFlow。

定位对齐先前结论：**可写、可批、可定时 → CLI**；MCP 留待后续薄封装检索/状态。

## 组件

```
ragc CLI
  ├─ kb create|list|show|delete
  ├─ ingest          追加文件正文
  ├─ sync            全量切分+embed+重建（主作业）
  ├─ query           hybrid 检索
  └─ chunk           仅预览切分
        │
        ├─ core/chunking.py     对齐 GEOFlow split_with_overlap
        ├─ core/embeddings.py   mock / OpenAI-compatible
        ├─ core/store.py        本地 JSON（~/.ragc/store.json）
        ├─ core/sync.py
        └─ core/retrieve.py     内存余弦 + 关键词合并
```

## Sync 语义

与 GEOFlow `KnowledgeChunkSyncService` 一致：**先清空该 KB 的 chunks，再全量重建**（非增量）。

## 明确不做（v0.1）

- 连接 GEOFlow PostgreSQL / Celery / pgvector
- PDF/DOCX 解析（仅 txt/md/csv/html）
- semantic_chunk LangGraph（旁路，见 content-LangGraph-CLI）
- MCP server（可后挂 `query` / `sync_status`）
