# RAG-CLI

独立 RAG / Embedding **生产作业** CLI：切分、同步重建、检索。

> **外挂**：不修改、不依赖运行中的 GEOFlow 闭环。契约对齐 v3 RAG，本地 JSON store + Mock embedding。见 [guide/geoflow-contract.md](./guide/geoflow-contract.md) 与仓库 [guide/cli-plugins.md](../guide/cli-plugins.md)。
## 安装

```bash
cd RAG-CLI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# 或直接 ./verify.sh
```

## 命令面

```bash
ragc kb create --name demo --demo
ragc kb list
ragc sync <kb_id>                 # 全量切分 + embedding（主作业）
ragc sync --demo                  # 离线一键：建库并 sync
ragc ingest <kb_id> --file doc.md [--sync]
ragc query <kb_id> "GEO 可见性"
ragc chunk --demo                 # 只预览切分
```

## 设计要点

| 能力 | 入口 | 说明 |
|------|------|------|
| 生产 sync | `ragc sync` | 删旧 chunks 全量重建（对齐 GEOFlow） |
| 检索 | `ragc query` | 向量 + 关键词 hybrid |
| 切分预览 | `ragc chunk` | 不落库 |
| MCP | （不做于本仓 v0.1） | 可后续薄封装 `query` / `status` |

数据默认：`~/.ragc/store.json`（可用 `--store` / `RAGC_STORE_PATH` 覆盖）。

## 验收

```bash
./verify.sh
```

## 文档

- [guide/architecture.md](./guide/architecture.md)
- [guide/geoflow-contract.md](./guide/geoflow-contract.md)
