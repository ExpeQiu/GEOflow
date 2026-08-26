# ADR-014：Techstore 只读导入 GEOFlow 知识库

- 状态：Accepted
- 日期：2026-08-26
- 相关：[ADR-011 Wiki](./ADR-011-GEOweb-Wiki轻量编辑台.md)、GEOweb [ADR-004](/Volumes/Lexar/git/03T/GEOweb/ADR/ADR-004-地图FAQ与Wiki真源.md)

## 决策

吉利技术知识**分轨导入**，禁止合成一张表：

| Techstore | GEOFlow | 用途 |
|-----------|---------|------|
| `Domain` / `Technique` | `tech_ip_assets` | 技术 IP 身份证 |
| 已发布 `Document`、FAQ、`knowledge` | `knowledge_bases`（按域拆 `Geely/{领域}`） | RAG 语料 |
| 地图树本身 | **不导入为 Wiki** | 运营结构仍在 Techstore |

只读：`TECHSTORE_DATABASE_URL`。未配置则用仓内 fixture。不写回 Techstore，不把 PDF 二进制当 SSOT。

## 入口

- Admin：`/production/knowledge` →「导入吉利知识库」
- API：`GET /api/admin/knowledge-bases/techstore-preview`、`POST /api/admin/knowledge-bases/import-techstore`
- CLI：`python scripts/import_techstore_knowledge.py`

幂等：按 KB 名称 / `ip_id` upsert。导入后排队 `sync-chunks`。

## 反模式

- 一个巨型知识库塞全量
- 把知识地图当 Wiki 真源
- 双向实时同步
