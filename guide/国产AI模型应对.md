产 AI 搜索差异化分析
主流产品一览
产品
背后
爬虫 UA（已知）
索引方式
秘塔AI搜索
秘塔科技
MetasoBot / AISpider
独立爬虫，主动索引
百度AI搜索
百度
BaiduSpider + 独立 UA
依赖百度传统索引 + AI 重排序
360AI搜索
360
360Spider
依赖 360 索引库
豆包
字节跳动
Bytespider
字节系内容优先
Kimi
Moonshot
KimiBot
独立爬虫
智谱 AI
智谱华元
ZhipuBot
独立爬虫
通义千问
阿里云
QwenBot
独立爬虫
核心差异 vs 西方
维度
西方（Perplexity/ChatGPT）
国产
爬虫协议遵守
高度遵守 robots.txt
秘塔等部分不遵守（与知网版权纠纷就是例子）
主动推送
Publisher API 有
基本没有成熟 API
索引依赖
独立爬虫
多依赖原有搜索引擎（百度/360）
内容策略
全文摘要 + 引用
注重信息流/公众号生态
备案要求
无
必须有 ICP 备案（无备案 = 不收录）
你的 GWEB 现状缺口
robots.txt 国产 UA（已在 `src/app/robots.ts` 补充）：
MetasoBot / BaiduSpider / 360Spider / Bytespider / KimiBot / ZhipuBot / QwenBot
允许 `/`，禁止 `/api/`、`/preview/`。
差异化对策
① robots.txt — 补充国产 UA（立即可做）
// src/app/robots.ts 新增 rules
{ userAgent: "MetasoBot", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "BaiduSpider", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "360Spider", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "Bytespider", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "KimiBot", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "ZhipuBot", allow: "/", disallow: ["/api/", "/preview/"] },
{ userAgent: "QwenBot", allow: "/", disallow: ["/api/", "/preview/"] },
② 备案是前置门槛（P0）
无 ICP 备案 = 百度/360/所有国产搜索不收录
这和 SEO 在中国的逻辑一样，GEO 同样依赖备案。GWEB 如果没有 ICP 备案，国产 AI 搜索（尤其是百度系）基本没戏。 先确认 GWEB 域名 aiforworld.cn 是否有已完成备案。
③ 百度是核心 — 需要单独对待
百度的 AI 搜索底层是百度 spider 抓取的页面被 LLM 处理，百度搜索收录 = 百度 AI 搜索可见。所以：
主动推送百度：URL 提交工具（百度搜索资源平台）
确保 sitemap.xml 被百度Spider抓取
百度有自己的 robots.txt 校验（比西方严格）
④ 秘塔等独立 AI 搜索 — 无法主动推送
秘塔有版权纠纷前科，不遵守 robots.txt 反而是常态。核心策略是：
让内容足够好（被主动抓取）
不需要额外做什么 robots.txt 配置（写了也不一定遵守）
⑤ 微信公众号生态借用
字节/微信内容在豆包/秘塔里有先天优势。GWEB 的 content/wiki/ 内容可以考虑：
同步分发到微信公众号（如果适合）
或在页面中嵌入微信公众号二维码（增加引用场景）