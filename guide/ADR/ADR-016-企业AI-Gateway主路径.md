# ADR-016：切换企业 AI Gateway 作为 LLM 主路径

- 状态：Accepted
- 日期：2026-08-27
- 取代：[ADR-015](./ADR-015-复用Lobster%20LLM网关.md) 中「吉利内网 = Lobster」为企业默认
- 参考：[企业 AI-API 直连网关](/Users/expeqiu/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/expe/Github/5-应用与场景/0-Guide/Geely开发指南/企业AI-API直连网关.md)

## 决策

GEOFlow **企业默认**走公司 **AI Gateway**（OpenAI 兼容文本端点），Lobster 降为本地 dev 遗留。

| 开关 | 含义 | 实际 base | 实际 Key |
|------|------|-----------|----------|
| **供应商资源** `vendor` | 公网厂商直连 | 模型表 `api_url` | 模型表 Key |
| **企业 AI Gateway** `geely` | 公司级 Gateway | `ENTERPRISE_AI_TEXT_BASE_URL` | `ENTERPRISE_AI_GATEWAY_API_KEY` |
| `auto` | 跟随 `.env` | 有企业 Key→Gateway，否则 Lobster Token→遗留，否则直连 | 同上 |

`connection_kind=inherit|enterprise-gateway|lobster|direct` 可按模型覆盖。

## 环境变量

```bash
LLM_GATEWAY_MODE=enterprise-gateway
ENTERPRISE_AI_GATEWAY_API_KEY=
ENTERPRISE_AI_TEXT_BASE_URL=https://ai-gateway-office.zeekrlife.com/v1
ENTERPRISE_AI_TEXT_MODEL=gpt-4o
AI_MOCK_MODE=false
```

一键注册：`python3 scripts/bootstrap_ai_from_env.py`

## 非目标

- 文生图/视频 AIGC 链路（`/aigc/api/v3/...`）本阶段不接入 GEOFlow 正文/RAG
- AIVIS 探针仍问 C 端产品，不经 Gateway

## Lobster 遗留

本地无企业 Key 时：`LLM_GATEWAY_MODE=lobster` + `LOBSTER_PROXY_TOKEN` + Eva `:56045`。
