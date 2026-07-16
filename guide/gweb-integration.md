# Gweb 集成说明（GEOFlow 后台 + Gweb 前台）

## 分工

| 系统 | 角色 |
|:---|:---|
| **GEOFlow** | 技术 IP 资产、Wiki 内容生产、GEO 门禁、Gweb 同步、溯源字段写入 |
| **Gweb** | Wiki 展现、Schema、llms.txt、sitemap、AI 主动提交 |

## 环境变量（GEOFlow）

```env
GEOFLOW_TECH_BRAND_MODE=true
GEOFLOW_PUBLIC_SITE_ENABLED=false   # 可选：关闭本站前台
GWEB_BASE_URL=https://tech.example.com
GWEB_REVALIDATE_SECRET=shared-secret
GWEB_SYNC_ENABLED=true
GWEB_ANALYTICS_URL=https://tech.example.com/admin/analytics
```

## Wiki Task 配置 SOP

1. 在 **技术 IP 资产** 中维护资产卡（`/geo_admin/tech-assets`）
2. 创建任务时选择 **内容格式 = Wiki 页面**
3. 发布范围自动锁定为 **仅渠道站点**
4. 绑定 **Gweb Wiki** 分发渠道（`channel_type=gweb_wiki`）
5. 选择 Wiki 专用 Prompt（概念/对比/指南/数据）

## 同步 API 契约（含溯源）

```
POST {GWEB_BASE_URL}/api/wiki/sync
Authorization: Bearer {GWEB_REVALIDATE_SECRET}

{
  "action": "upsert",
  "slug": "shen-dun-battery",
  "type": "concept",
  "route_prefix": "concepts",
  "geo_task_id": "1234",
  "geo_content_hash": "abc123def456",
  "frontmatter": { ... },
  "body": "Markdown 正文",
  "mdx": "---\n...\n---\n\n正文"
}
```

GWEB 写入 MDX frontmatter：

- `geo_flow_task` — 溯源到 GEOFlow Task（无任务时回退 Article.id）
- `geo_content_hash` — 内容指纹；相同则跳过写盘
- `last_synced_at` / `source=geoflow`

成功后 GEOFlow 会调用 `POST /api/revalidate` 刷新 ISR，并可选调用 `POST /api/ai-submit`。

## AI 主动提交

```
POST {GWEB_BASE_URL}/api/ai-submit
Authorization: Bearer {GWEB_REVALIDATE_SECRET}

{ "urls": ["https://aiforworld.cn/concepts/shen-dun-battery"] }
```

GWEB 侧环境变量（可选）：`PERPLEXITY_API_KEY`、`BING_WEBMASTER_APIKEY`、`BING_SITE_URL`。

## GEO 门禁（Wiki）

`content_format=wiki_mdx` 时追加检查：快速结论、表格、内链≥3、FAQ≥2、更新日期、Schema、证据链。

配置：`GEO_EVAL_WIKI_GATE_ENABLED=true`

## 路线图映射

| 步骤 | GEOFlow | Gweb |
|:---|:---|:---|
| Step 0–1 | tech_ip_assets | — |
| Step 2 生产 | Wiki Task + Prompt | MDX 渲染 + geo_flow_task |
| Step 2 展现 | gweb_wiki 同步 | concepts/compare/... |
| Step 2 索引 | 发布后 ai-submit | Perplexity / Bing |
| Step 5 | Strategy Hub KPI + Gweb 对齐率 | 流量入口 / pages.json 对齐 |

详见 `guide/AI溯源链路设计.md`。
