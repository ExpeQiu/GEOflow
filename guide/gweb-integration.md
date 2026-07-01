# Gweb 集成说明（GEOFlow 后台 + Gweb 前台）

## 分工

| 系统 | 角色 |
|:---|:---|
| **GEOFlow** | 技术 IP 资产、Wiki 内容生产、GEO 门禁、Gweb 同步 |
| **Gweb** | Wiki 展现、Schema、llms.txt、sitemap |

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

## 同步 API 契约

```
POST {GWEB_BASE_URL}/api/wiki/sync
Authorization: Bearer {GWEB_REVALIDATE_SECRET}

{
  "action": "upsert",
  "slug": "shen-dun-battery",
  "type": "concept",
  "route_prefix": "concepts",
  "frontmatter": { ... },
  "body": "Markdown 正文",
  "mdx": "---\n...\n---\n\n正文"
}
```

成功后 GEOFlow 会调用 `POST /api/revalidate` 刷新 ISR。

## GEO 门禁（Wiki）

`content_format=wiki_mdx` 时追加检查：快速结论、表格、内链≥3、FAQ≥2、更新日期、Schema、证据链。

配置：`GEO_EVAL_WIKI_GATE_ENABLED=true`

## 路线图映射

| 步骤 | GEOFlow | Gweb |
|:---|:---|:---|
| Step 0–1 | tech_ip_assets | — |
| Step 2 生产 | Wiki Task + Prompt | MDX 渲染 |
| Step 2 展现 | gweb_wiki 同步 | concepts/compare/... |
| Step 5 | Strategy Hub KPI | 流量 / pages.json |
