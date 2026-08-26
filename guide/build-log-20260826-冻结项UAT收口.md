# 构建日志 2026-08-26 · 冻结项与 UAT 收口

## 做了什么

- 三套 CLI：README 标归档；RAG / content-lg 补 `start.sh`（只跑 verify）
- 六语言：顶栏/登录 zh·en·ja·ko·de·fr 骨架，正文回退中文
- 文章 CMS：仪表盘自动化与运营总览主入口改 Wiki；`/operations/articles` 仍 200
- 不新增渠道类型；`.env.example` 补 DOUBAO_*；通义/文心/元宝标明走 C 端
- `scripts/smoke_probe_keys.sh` + `tests/test_platform_uat.py`（缺 Key / 无 GEOFLOW_LIVE_PROBE 跳过）
- `GET /knowledge-bases/embedding-ready`、`POST /knowledge-bases/reindex-all`、`scripts/reindex_all_knowledge.py`（Mock 拒绝）

## 验收

```bash
cd geoflow-v3 && ./scripts/verify-services.sh
./scripts/smoke_probe_keys.sh
```
