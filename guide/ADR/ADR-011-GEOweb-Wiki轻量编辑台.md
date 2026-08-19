# ADR-011：GEOweb Wiki 轻量编辑台（GEOFlow Admin）

- 状态：Accepted（Wave 1–3 已落地）
- 日期：2026-08-19
- 相关：[ADR-010 Theme](./ADR-010-Theme主题包主链路.md)、GEOweb [ADR-004](/Volumes/Lexar/git/03T/GEOweb/ADR/ADR-004-地图FAQ与Wiki真源.md)

## 决策

在 **GEOFlow Admin（运营 Hub）** 做轻量 Wiki 编辑台，维护 GEOweb `/wiki` 九类页。  
**不**放进 Techstore；Techstore 只维护 `/map` `/qa` PMS 素材。

挂在现有 GEOFlow v3（FastAPI + geoflow-admin），不新开仓。复用 `Article`（`content_format=wiki_mdx`）+ `GeowebPublisher`，不另建 Wiki 表。

## 轻量指什么

| 做 | 不做（首期） |
|--|--|
| 按 type 列表、筛选、搜索 | 可视化 MDX 画布 / 组件拖拽 |
| 表单填 content-schema 字段 + Markdown 正文 | 在 Techstore 开 Wiki CRUD |
| 一键发布到 GEOweb（已有 sync） | 直写 GEOweb 磁盘/SSH |
| 打开 GEOweb 预览 URL | 完整 CMS 权限/工作流（沿用 Article 草稿/审核） |
| 隐藏 smoke/probe 页 | 知识库自动成稿（二期） |

## 信息架构

入口：运营 Hub → **Wiki**（与「文章」并列，不要混进文章列表）。

```
/operations/wiki              按 type 分栏：concept/compare/guide/…
/operations/wiki/new          新建
/operations/wiki/[id]         编辑 + 发布 + 预览
```

数据仍是 `articles`：`content_format=wiki_mdx`，`wiki_meta` 存 schema 字段。长文 `type=article` 可进本台，也可留在现有「文章」——**本台以九类 Wiki 为主，`article` 作可选 type**。

## 编辑字段（对齐 GEOweb content-schema）

必填：`title` `slug` `type` `body` `geo_flow_task`（无任务则用 article.id）。  
建议：`domain` `quick_answer` `core_takeaway` `target_query` `related[]` `faq[]` `schema_type` `geo_theme_id`。

发布走现有 `POST {GEOWEB}/api/geoflow/sync`。预览：`{GEOWEB_BASE_URL}/{route}/{slug}`。

## 分期与 DoD

### Wave 1（可验收增量，约 1–2 天）

- 列表：仅 `wiki_mdx`，按 type、slug、是否已 sync（`wiki_meta.geoweb_url` / `geo_content_hash`）
- 新建/编辑：上列字段；保存写 `wiki_meta`
- 「发布到 GEOweb」调用现有分发（`channel_type=geoweb`）
- 过滤 slug 含 `smoke|probe|interop`
- DoD：新建一条 `type=concept` → 发布 → `http://127.0.0.1:3070/concepts/{slug}` 200，frontmatter `source: geoflow`

### Wave 2

- `related` 自动补全（本台已发布页）
- compare/guide 校验：FAQ≥3、related≥3，不通过仍可存草稿、不可发布
- 知识库：选 KB → 生成草稿正文（Mock First）

### Wave 3

- Theme 包看板（子页先于 topic hub）
- 接 `sync-pack`
- 与 GEOweb `/api/pages.json` 对账（仅 geoflow、非 smoke）

## 文件落点（Wave 1）

| 层 | 路径 |
|----|------|
| Admin 导航 | `apps/geoflow-admin/lib/nav-config.ts` 增 `operations/wiki` |
| 页面 | `apps/geoflow-admin/app/(dashboard)/operations/wiki/` |
| API | `GET/POST /api/admin/wiki`、`PATCH /api/admin/wiki/{id}`、`POST /api/admin/wiki/{id}/publish` |
| 服务 | `backend/app/services/admin/wiki_editor_service.py` |
| 契约 | 字段校验对齐 GEOweb `src/lib/geoflow/sync.ts` Zod |

Wave 1 入口：运营 Hub → **Wiki**。发布委托 `GeowebPublisher`；slug 含 `smoke|probe|interop` 默认不出现在列表且不可发布。

## Wave 1 验收（2026-08-19）

- Admin：`http://127.0.0.1:13001/operations/wiki`
- 新建 `concept` `wiki-editor-wave1` → 发布 → `http://127.0.0.1:3070/concepts/wiki-editor-wave1` 200，frontmatter `source: geoflow`
- 单测：`backend/tests/test_wiki_editor.py`
- 与 GEOweb `/wiki` 对齐：`POST /api/admin/wiki/import-geoweb` 导入种子页；GEOweb 目录隐藏 smoke/probe/interop。当前双方均为 19 页。

## Wave 2 验收（2026-08-19）

- related：`GET /api/admin/wiki/related-options`，编辑台检索已发布页并写入 `concepts/{slug}` 路径
- compare/guide：FAQ≥3 且 related≥3 才可 `POST /wiki/{id}/publish`；PATCH 草稿仍可保存
- 知识库：`POST /api/admin/wiki/generate-draft`，`AI_MOCK_MODE=true` 用 RAG 命中或 Mock 骨架填正文

## Wave 3 验收（2026-08-19）

- Theme 包看板：`/operations/wiki/packs`，子页先于 topic hub
- `POST /api/admin/wiki/packs/{theme_id}/sync-pack` → GEOweb `POST /api/geoflow/sync-pack`；compare/guide 未过门禁则 422 整包不发
- 对账：`GET /api/admin/wiki/reconcile` 对照 GEOweb `/api/pages.json`（geoflow / 非 smoke）；pages.json 带 `source`

## 反模式

- 在 Techstore `/admin` 加 Wiki 编辑
- 编辑台直接改 GEOweb `content/wiki/**` 文件
- 与 PMS 长页（`/techGene`）混为一谈
- 把探针题原文当 Wiki 标题（见 ADR-010）

## 后果

- 运营改 Wiki 只进 GEOFlow；GEOweb 仍是发布站
- 知识库是语料，编辑台是定稿出口
- Techstore 技术点最多挂 Wiki URL，不存正文
