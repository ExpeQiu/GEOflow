# GWEB × GEOFlow AI 搜索索引溯源链设计方案

> **状态更新 2026-08-13**：官方发布站已切换为 **GEOweb**；下文中的 GWEB / `gweb_wiki` / `/api/wiki/sync` 为历史设计。  
> 现行契约见 [geoweb-integration.md](./geoweb-integration.md) 与 GEOweb `guide/geoflow-sync.md`。  
> 现行发布器是 **GeowebPublisher**（不是 `GwebWikiPublisher`）。Gweb 仓库保留为独立项目前台，不再由 GEOFlow 分发。


> 版本：v1.1
> 日期：2026-07-16
> 作者：小二（指挥官）
> 状态：已落地（M1–M4）

---

## 一、背景与目标

### 1.1 背景

GWEB 是公网技术 Wiki 系统，基于 Next.js 构建，已具备良好的 SEO 基础（sitemap.xml、JSON-LD Schema、robots.txt 允许 AI 爬虫）。

GEOFlow v3 是面向 GEO（生成式引擎优化）的智能内容工程平台，负责 Wiki 内容生产与分发。

当前两个系统的对接链路未完成，存在以下问题：

- GWEB 的 `llms.txt` 端点缺失（函数已写好但无 route handler）
- GEOFlow 缺少 GwebWikiPublisher（只有 WordPress / Generic HTTP / Agent 三种发布器）
- 缺乏 AI 搜索主动推送机制（Perplexity、Bing Webmaster）
- 缺乏内容溯源体系（无法从 AI 答案追踪到 GEOFlow 任务）

### 1.2 目标

1. **打通数据链路**：GEOFlow 生产 → GWEB 展示 → AI 搜索索引
2. **建立溯源标记**：AI 引用的内容可反向追溯到 GEOFlow 任务 ID
3. **主动推送**：不依赖被动爬取，主动向 AI 搜索引擎提交 URL
4. **被动可验证**：可验证 GWEB Wiki 内容是否被 AI 索引

---



## 二、现状分析



### 2.1 GWEB 已有能力


| 能力                 | 实现方式                                                           | 状态                                                                                      |
| ------------------ | -------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| robots.txt         | `src/app/robots.ts`                                            | ✅ 允许 PerplexityBot、ChatGPT-User、Claude-SearchBot、GPTBot、ClaudeBot、CCBot、Google-Extended |
| sitemap.xml        | `src/app/sitemap.ts`                                           | ✅ 含优先级 + lastMod，全站覆盖                                                                   |
| JSON-LD Schema     | `src/lib/wiki/schema.ts` → `buildWikiPageSchemas()`            | ✅ 按 type 切换：TechArticle / FAQPage / HowTo / Dataset                                     |
| BreadcrumbList     | `src/lib/schema/breadcrumb.ts`                                 | ✅ 每个 Wiki 页面都有                                                                          |
| /api/pages.json    | `src/app/api/pages.json/route.ts` → `buildWikiPagesJson()`     | ✅ 机器可读全页索引                                                                              |
| /api/profile.json  | `src/app/api/profile.json/route.ts` → `buildWikiProfileJson()` | ✅ 品牌画像                                                                                  |
| /api/wiki/sync     | `src/app/api/wiki/sync/route.ts`                               | ✅ 接收 GEOFlow 推送，写入 MDX                                                                  |
| buildLlmsTxt()     | `src/lib/wiki/geo-export.ts`                                   | ✅ 函数已写好，**但无 route handler**                                                            |
| buildLlmsFullTxt() | `src/lib/wiki/geo-export.ts`                                   | ✅ 函数已写好，**但无 route handler**                                                            |


**关键缺口（历史，已修复）：**

- ~~`llms.txt` → 文件存在但内容为空~~ → 现由 `src/app/llms.txt/route.ts` 动态生成
- ~~`llms-full.txt` → 不存在~~ → 现由 `src/app/llms-full.txt/route.ts` 动态生成



### 2.2 GEOFlow v3 已有能力


| 能力                         | 位置                                                | 状态                              |
| -------------------------- | ------------------------------------------------- | ------------------------------- |
| Article.wiki_meta (JSON)   | `app/models/article.py`                           | ✅ 可存储 task_id、content_hash      |
| content_format=wiki_mdx    | `app/models/article.py`                           | ✅ 支持 Wiki 格式                    |
| DistributionChannel 模型     | `app/models/distribution.py`                      | ✅ 支持 channel_type + config_json |
| ArticleDistribution 记录     | `app/models/distribution.py`                      | ✅ 记录发布结果                        |
| GwebWikiPublisher          | `app/services/geoflow/gweb_wiki_publisher.py` | ✅ 含 geo_task_id / geo_content_hash / ai-submit |
| geo_task_id 写入 frontmatter | GWEB wiki sync + Publisher                    | ✅ |
| Perplexity/Bing 主动推送       | GWEB `/api/ai-submit`                         | ✅ 密钥可选 |


---



## 三、系统架构



### 3.1 完整数据流

```
GEOFlow Task (id=1234, content_format=wiki_mdx)
    │
    ▼
content_agent 生产 MDX 内容
    │
    ▼
写入 Article.wiki_meta：
{
  "wiki_page_type": "concept",
  "route_prefix": "concepts",
  "frontmatter": { "title": "...", "tags": [...] },
  "mdx": "---...\n正文",
  "content_hash": "sha256:abc123"
}
    │
    ▼
Distribution 触发 GwebWikiPublisher
    │
    ▼
POST https://aiforworld.cn/api/wiki/sync
{
  "action": "upsert",
  "slug": "shen-dun-battery",
  "type": "concept",
  "route_prefix": "concepts",
  "geo_task_id": "1234",           ← 新增溯源字段
  "geo_content_hash": "abc123",    ← 新增内容指纹
  "frontmatter": { ... },
  "body": "Markdown 正文",
  "mdx": "---..."
}
    │
    ▼ GWEB wiki sync API
写入 /content/wiki/concepts/shen-dun-battery.mdx
frontmatter 注入：
  geo_flow_task: "1234"
  geo_content_hash: "abc123"
  last_synced_at: "2026-07-16T..."
    │
    ▼
Next.js ISR 重新渲染页面
JSON-LD 中 @id = https://aiforworld.cn/concepts/shen-dun-battery#article
    │
    ▼
POST /api/ai-submit → 推送 Perplexity + Bing
    │
    ▼
AI 搜索索引收录
    │
    ▼ 用户查询
AI 回答：「根据 https://aiforworld.cn/concepts/shen-dun-battery（ GEOFlow 任务 #1234）」
    │
    ▼ 可溯源
点击链接 → GWEB 页面
<meta> 或页面底部显示 geo_flow_task: 1234
```



### 3.2 技术组件对应关系


| 组件                        | 归属      | 职责                    |
| ------------------------- | ------- | --------------------- |
| GEOFlow Backend (FastAPI) | GEOFlow | 内容生产、任务管理、分发触发        |
| GwebWikiPublisher         | GEOFlow | 调用 GWEB wiki sync API |
| GWEB Next.js App          | GWEB    | Wiki 渲染、Schema 输出、ISR |
| wiki sync API             | GWEB    | 接收 MDX，写入文件系统         |
| /api/ai-submit            | GWEB    | 主动推送 URL 到 AI 搜索引擎    |
| Perplexity Publisher API  | 外部      | AI 搜索索引               |
| Bing Webmaster API        | 外部      | Bing 搜索索引             |


---



## 四、详细设计



### 4.1 GWEB 侧改动



#### 4.1.1 新增 llms.txt 端点

**文件：** `src/app/llms.txt/route.ts`

```typescript
import { NextResponse } from "next/server";
import { buildLlmsTxt } from "@/lib/wiki/geo-export";

export const dynamic = "force-dynamic";

export async function GET() {
  const content = await buildLlmsTxt();
  return new NextResponse(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
```



#### 4.1.2 新增 llms-full.txt 端点

**文件：** `src/app/llms-full.txt/route.ts`

```typescript
import { NextResponse } from "next/server";
import { buildLlmsFullTxt } from "@/lib/wiki/geo-export";

export const dynamic = "force-dynamic";

export async function GET() {
  const content = await buildLlmsFullTxt();
  return new NextResponse(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800",
    },
  });
}
```



#### 4.1.3 改造 wiki sync API（注入溯源字段）

**文件：** `src/app/api/wiki/sync/route.ts`

**新增字段处理：**

```typescript
// 在 upsert path 中，MDX 写入前：
const geoMeta = {
  ...frontmatter,
  geo_flow_task: body.geo_task_id ?? null,        // 溯源到 GEOFlow 任务
  geo_content_hash: body.geo_content_hash ?? null, // 内容指纹
  last_synced_at: new Date().toISOString(),        // 同步时间
  source: "geoflow",
};

const mdx =
  typeof body.mdx === "string" && body.mdx.trim() !== ""
    ? body.mdx
    : matter.stringify(markdownBody, { ...geoMeta, slug, type });
```

**body 类型扩展：**

```typescript
let body: {
  // ... 现有字段
  geo_task_id?: string;       // 新增
  geo_content_hash?: string;  // 新增
};
```



#### 4.1.4 新增 AI 主动提交 API

**文件：** `src/app/api/ai-submit/route.ts`

```typescript
import { NextResponse } from "next/server";

const PERPLEXITY_API_URL = "https://api.perplexity.ai/v1/publish";
const BING_WEBMASTER_API = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl";

interface SubmitResult {
  url: string;
  perplexity?: { ok: boolean; error?: string };
  bing?: { ok: boolean; error?: string };
}

export async function POST(request: Request) {
  const { urls, perplexityApiKey, bingApiKey, bingSiteUrl } = await request.json();

  if (!urls || !Array.isArray(urls) || urls.length === 0) {
    return NextResponse.json({ error: "urls 为空" }, { status: 400 });
  }

  const results: SubmitResult[] = [];

  for (const url of urls) {
    const result: SubmitResult = { url };

    // 1. Perplexity Publisher
    if (perplexityApiKey) {
      try {
        const pr = await fetch(PERPLEXITY_API_URL, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${perplexityApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ url }),
        });
        result.perplexity = pr.ok
          ? { ok: true }
          : { ok: false, error: `HTTP ${pr.status}` };
      } catch (e: any) {
        result.perplexity = { ok: false, error: e.message };
      }
    }

    // 2. Bing Webmaster
    if (bingApiKey && bingSiteUrl) {
      try {
        const br = await fetch(
          `${BING_WEBMASTER_API}?siteUrl=${encodeURIComponent(bingSiteUrl)}&url=${encodeURIComponent(url)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              // Bing 需要 apikey 作为 query param，这里简化为 header 方式
            },
          }
        );
        result.bing = br.ok
          ? { ok: true }
          : { ok: false, error: `HTTP ${br.status}` };
      } catch (e: any) {
        result.bing = { ok: false, error: e.message };
      }
    }

    results.push(result);
  }

  return NextResponse.json({
    submittedAt: new Date().toISOString(),
    total: urls.length,
    results,
  });
}
```

**环境变量：**

```env
PERPLEXITY_API_KEY=   # 可选，有则主动推 Perplexity
BING_WEBMASTER_APIKEY= # 可选
BING_SITE_URL=        # 可选
```



#### 4.1.5 Wiki 页面 JSON-LD 增强溯源

**文件：** `src/lib/wiki/schema.ts`

```typescript
// 在 buildWikiPageSchemas() 的 TechArticle 分支中，增加：
{
  "@id": pageUrl(routePrefix, meta.slug) + "#article",
  "isBasedOn": meta.geo_flow_task
    ? {
        "@type": "CreativeWork",
        name: `GEOFlow 任务 #${meta.geo_flow_task}`,
        identifier: meta.geo_flow_task,
        // 如有任务页面可加 URL
      }
    : undefined,
}.filter(Boolean)
```

> 注：需在 WikiPage 类型中增加 `geo_flow_task?: string` 字段。

---



### 4.2 GEOFlow 侧改动



#### 4.2.1 新增 GwebWikiPublisher

**文件：** `backend/app/services/geoflow/gweb_publisher.py`（新建）

```python
"""GWEB Wiki 分发发布器。"""

import hashlib
import httpx
from typing import Any

from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import DistributionChannel

logger = get_logger("geoflow.publishers.gweb")


def _cfg(channel: DistributionChannel) -> dict[str, Any]:
    return channel.config_json if isinstance(channel.config_json, dict) else {}


def _content_hash(content: str) -> str:
    """计算内容指纹，用于判断是否真正变化。"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def publish_gweb_wiki(channel: DistributionChannel, article: Article) -> dict:
    """
    调用 GWEB /api/wiki/sync，将 MDX 内容发布到 GWEB Wiki。

    config 必填字段：
        gweb_base_url  : GWEB 站点根 URL，如 https://aiforworld.cn
        gweb_secret    : GWEB_REVALIDATE_SECRET
    可选字段：
        route_prefix   : 默认从 wiki_meta.route_prefix 读取
    """
    config = _cfg(channel)
    base_url = config.get("gweb_base_url")
    secret = config.get("gweb_secret")

    if not base_url or not secret:
        raise RuntimeError("gweb_publisher_missing_config: gweb_base_url 或 gweb_secret 未配置")

    # 解析 wiki_meta
    wiki_meta = article.wiki_meta or {}
    wiki_type = wiki_meta.get("wiki_page_type", "concept")
    route_prefix = wiki_meta.get("route_prefix") or _default_route_prefix(wiki_type)
    mdx_content = wiki_meta.get("mdx", "")
    frontmatter = wiki_meta.get("frontmatter", {})

    # 计算内容指纹
    content_hash = _content_hash(mdx_content or article.content or "")

    payload = {
        "action": "upsert",
        "slug": article.slug,
        "type": wiki_type,
        "route_prefix": route_prefix,
        # 溯源字段
        "geo_task_id": str(article.id),
        "geo_content_hash": content_hash,
        # 内容
        "frontmatter": frontmatter,
        "body": article.content or "",
        "mdx": mdx_content,
    }

    endpoint = f"{base_url.rstrip('/')}/api/wiki/sync"
    headers = {"Authorization": f"Bearer {secret}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise RuntimeError(f"gweb_wiki_http_{resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    remote_url = data.get("url") or f"{base_url}/{route_prefix}/{article.slug}"

    logger.info(
        "gweb_wiki_published",
        article_id=article.id,
        slug=article.slug,
        geo_task_id=str(article.id),
        remote_url=remote_url,
    )

    return {
        "url": remote_url,
        "remote_id": article.slug,
        "geo_task_id": str(article.id),
        "geo_content_hash": content_hash,
    }


def _default_route_prefix(wiki_type: str) -> str:
    mapping = {
        "concept": "concepts",
        "compare": "compare",
        "guide": "guides",
        "glossary": "glossary",
        "data": "data",
        "thread": "threads",
        "topic": "topics",
        "article": "articles",
        "certification": "certifications",
    }
    return mapping.get(wiki_type, "concepts")
```



#### 4.2.2 注册发布器

**文件：** `backend/app/services/geoflow/distribution_publishers.py`

```python
# 在文件顶部或适当位置 import
from .gweb_publisher import publish_gweb_wiki

# 在 publish() 调度函数中添加：
PUBLISHER_MAP = {
    "geoflow_agent": publish_geoflow_agent,
    "wordpress": publish_wordpress,
    "generic_http": publish_generic_http,
    "gweb_wiki": publish_gweb_wiki,  # 新增
}
```



#### 4.2.3 前端配置界面（geoflow-admin）

**文件：** `apps/geoflow-admin/src/app/admin/channels/new/page.tsx`（或类似路径）

新增 `gweb_wiki` channel_type 配置表单：


| 字段            | 类型          | 说明                      |
| ------------- | ----------- | ----------------------- |
| gweb_base_url | string      | GWEB 站点 URL             |
| gweb_secret   | string      | GWEB_REVALIDATE_SECRET  |
| route_prefix  | string (可选) | 默认按 wiki_page_type 自动推断 |




#### 4.2.4 触发 AI 搜索提交（可选/后续）

在 Distribution 完成并成功发布后，追加一步：

```python
# 在 distribution_publishers.py 或单独的 ai_submit.py 中
async def submit_to_ai_search(urls: list[str]):
    """发布成功后主动推送到 AI 搜索引擎。"""
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            f"{settings.GWEB_BASE_URL}/api/ai-submit",
            json={
                "urls": urls,
                "perplexityApiKey": settings.PERPLEXITY_API_KEY,
                "bingApiKey": settings.BING_WEBMASTER_APIKEY,
                "bingSiteUrl": settings.BING_SITE_URL,
            },
        )
```

---



## 五、环境变量汇总



### GWEB 侧（.env.local / .env.production）

```env
# AI 搜索主动提交（可选）
PERPLEXITY_API_KEY=         # Perplexity Publisher API Key
BING_WEBMASTER_APIKEY=      # Bing Webmaster API Key
BING_SITE_URL=https://aiforworld.cn
```



### GEOFlow 侧（.env）

```env
# GWEB Wiki 分发（channel config_json 中配置，也可放这里）
GWEB_BASE_URL=https://aiforworld.cn
GWEB_REVALIDATE_SECRET=     # 与 GWEB 侧一致
```

---



## 六、验收标准



### 6.1 功能验收


| 用例                | 验收条件                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| llms.txt 端点       | `GET /llms.txt` 返回非空品牌说明 + 核心页面列表，HTTP 200                               |
| llms-full.txt 端点  | `GET /llms-full.txt` 返回全站页面摘要，HTTP 200                                   |
| wiki sync 溯源      | POST /api/wiki/sync 后，MDX frontmatter 含 geo_flow_task + geo_content_hash |
| GwebWikiPublisher | 触发 Distribution 后，GWEB 侧 MDX 文件正确写入                                      |
| AI Submit API     | POST /api/ai-submit 返回 submittedAt + results 数组                          |




### 6.2 可验证性


| 验证方式          | 操作                                        |
| ------------- | ----------------------------------------- |
| Perplexity 索引 | 发布后在 Perplexity 搜索 site:aiforworld.cn 关键词 |
| ChatGPT       | 开启 Browse 后问关于 GWEB Wiki 内容的具体问题          |
| Bing          | Bing Webmaster → URL Inspection 查看是否被抓取   |


---



## 七、里程碑拆解


| 阶段     | 内容                                          | 工作量  | 负责         |
| ------ | ------------------------------------------- | ---- | ---------- |
| **M1** | GWEB：llms.txt + llms-full.txt route handler | 1h   | GWEB 开发    |
| **M1** | GWEB：wiki sync 溯源字段注入                       | 0.5h | GWEB 开发    |
| **M2** | GEOFlow：GwebWikiPublisher 实现                | 2h   | GEOFlow 开发 |
| **M2** | GEOFlow：admin 渠道配置界面                        | 1h   | GEOFlow 开发 |
| **M3** | GWEB：AI Submit API                          | 2h   | GWEB 开发    |
| **M3** | Perplexity / Bing 接入调试                      | 2h   | 双方联调       |
| **M4** | JSON-LD 溯源链增强（可选）                           | 1h   | GWEB 开发    |


---



## 八、风险与依赖


| 风险                   | 影响     | 缓解                                |
| -------------------- | ------ | --------------------------------- |
| Perplexity API 申请被拒  | 无法主动推送 | 依赖被动爬取，robots.txt 已开放             |
| GWEB 大量页面发布触发 ISR 风暴 | 源站性能   | 加 `revalidate_paths` 节流，或前台关闭 ISR |
| wiki sync 频繁推送但内容无变化 | 浪费资源   | geo_content_hash 对比，只在变化时触发       |
| llms.txt 体积过大        | 超时或被截断 | buildLlmsTxt() 已限制 20 条核心页面       |


---



## 九、相关文件索引



### GWEB 侧


| 文件                               | 作用                                 |
| -------------------------------- | ---------------------------------- |
| `src/app/llms.txt/route.ts`      | **新建**：llms.txt 端点                 |
| `src/app/llms-full.txt/route.ts` | **新建**：llms-full.txt 端点            |
| `src/app/api/wiki/sync/route.ts` | **改造**：增加 geo_task_id 注入           |
| `src/app/api/ai-submit/route.ts` | **新建**：AI 搜索主动提交                   |
| `src/lib/wiki/schema.ts`         | **改造**：JSON-LD 增加溯源链               |
| `src/lib/wiki/geo-export.ts`     | 已有：buildLlmsTxt / buildLlmsFullTxt |
| `src/lib/wiki/types.ts`          | 需增：WikiPageMeta.geo_flow_task 字段   |




### GEOFlow 侧


| 文件                                                        | 作用                       |
| --------------------------------------------------------- | ------------------------ |
| `backend/app/services/geoflow/gweb_publisher.py`          | **新建**：GwebWikiPublisher |
| `backend/app/services/geoflow/distribution_publishers.py` | **改造**：注册 gweb_wiki 类型   |
| `apps/geoflow-admin/src/app/admin/channels/`              | **改造**：新增 gweb_wiki 配置表单 |


---



## 十、附录



### A. Perplexity Publisher API

文档：[https://docs.perplexity.ai/docs/publisher-api](https://docs.perplexity.ai/docs/publisher-api)

端点：`POST https://api.perplexity.ai/v1/publish`
认证：Bearer Token（个人/公司 Publisher Plan）

### B. Bing Webmaster API

文档：[https://www.bing.com/webmasters/help/webmaster-api-9e80e8a8](https://www.bing.com/webmasters/help/webmaster-api-9e80e8a8)

端点：`GET/POST https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl`
认证：API Key（免费申请）

### C. AI 搜索索引验证命令

```bash
# 检查 llms.txt
curl -s https://aiforworld.cn/llms.txt | head -30

# 检查 llms-full.txt
curl -s https://aiforworld.cn/llms-full.txt | wc -l

# 检查某页面 JSON-LD
curl -s https://aiforworld.cn/concepts/shen-dun-battery | grep -o 'application/ld+json' -A 100 | head -50

# 验证 sitemap
curl -s https://aiforworld.cn/sitemap.xml | grep '<loc>' | wc -l
```

