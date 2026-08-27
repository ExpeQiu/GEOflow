# ADR-015：复用企业 Lobster 作为 LLM 网关

- 状态：Superseded（企业默认见 [ADR-016](./ADR-016-企业AI-Gateway主路径.md)）
- 日期：2026-08-26
- 相关：[企业级 API 设计](/Users/expeqiu/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/expe/Github/5-应用与场景/0-Guide/Geely开发指南/企业级API设计.md)

## 决策

GEOFlow 提供 **API 资源双档开关**（Admin 可切，写入 `site_settings.llm_api_resource`，优先于 `.env`）：

| 开关 | 含义 | 实际 base | 实际 Key |
|------|------|-----------|----------|
| **供应商资源** `vendor` | 对接公网厂商 | 模型表 `api_url` | 模型表 Key |
| **吉利内网资源** `geely` | 对接 Eva Lobster | `{LOBSTER_PROXY_BASE}/v1/geely/{vendor}/v1` | `LOBSTER_PROXY_TOKEN` |
| `auto` | 跟随 `.env` `LLM_GATEWAY_MODE` | 有 Token→内网，否则供应商 | 同上 |

`connection_kind=inherit|lobster|direct` 可按模型覆盖全局开关。

企业默认建议：`geely` + Token；本地无 Eva：`vendor`。

## 非目标

- 不在 GEOFlow 内再实现配额/审计/内容过滤（网关职责）
- AIVIS 探针仍问 C 端产品（豆包/Kimi 搜索），**不经** Lobster

## 配置

```
LLM_GATEWAY_MODE=auto
LOBSTER_PROXY_BASE=http://127.0.0.1:56045
LOBSTER_PROXY_TOKEN=
LOBSTER_API_ROOT=v1
```

Admin：`/production/ai-models` 顶部双档开关；`GET/PATCH /api/admin/ai-gateway`。
需要 `alembic upgrade head`（019 vendor / connection_kind）。
