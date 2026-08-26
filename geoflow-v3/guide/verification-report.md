# GEOFlow v3 验证报告

> 更新：2026-08-26

## 升级计划完成项

| Wave | 内容 | 状态 |
|------|------|------|
| Wave 0–4 | 基础闭环、分发、Materials | 完成 |
| **Wave A–D** | AIVIS 场景/缺口/报告 | 完成 |
| **P0 真实闭环** | strict API、remediation lift、GEOweb 对齐 | 完成 |
| **北极星 KPI** | Top3/pp、质量灯、信源章 | 完成 |
| **产品面收口（ADR-013）** | 导航 10 Tab、实验室、pipeline/geoweb 默认、legacy 410 | 完成 |
| **冻结项/UAT 收口** | CLI 归档脚本、六语言顶栏、Wiki 主入口、探针矩阵、全库重嵌 | 完成 |

## 本地验证

```bash
cd geoflow-v3 && ./scripts/verify-services.sh
.venv/bin/python -m pytest tests/test_product_trim.py tests/test_platform_uat.py -m "not live" -q
```

Admin 冒烟：登录 → 顶栏语言切换 → 诊断 → 探针日扫 → 主题包 → Wiki。  
实验室直链仍可用：`/strategy/sales-copy`、`/operations/articles`。

## AIVIS / 北极星 smoke 端点

- `GET /api/admin/strategy/diagnosis` → `monitor.top3_pct` / `gap_vs_leader_top3_pp`
- `POST /api/admin/strategy/monitor/scenes/{id}/create-task?legacy_direct_task=true` → **410**
- `GET /api/admin/distribution/form-options` → `channel_types=["geoweb"]`
- `GET /api/admin/knowledge-bases/embedding-ready` → `mode` / `ready`

## 六平台 Key 矩阵

| 平台 | 路径 | 环境变量 |
|------|------|----------|
| 豆包 / DeepSeek / Kimi | Open API | `DOUBAO_API_KEY`+`DOUBAO_MODEL` / `DEEPSEEK_API_KEY` / `KIMI_API_KEY` |
| 通义 / 文心 / 元宝 | C 端 Playwright | `CEND_*` + 登录 Profile，无 Open API Connector |

```bash
./scripts/smoke_probe_keys.sh
GEOFLOW_LIVE_PROBE=1 ./scripts/smoke_probe_keys.sh   # 真 Key
```

## 全库重嵌

1. 生产 `.env`：`AI_MOCK_MODE=false`，Admin 配置 embedding 模型
2. 重启 API + Worker
3. `python scripts/reindex_all_knowledge.py` 或知识库页「全库重嵌」
4. Mock 模式脚本会拒绝执行（exit 2）

## 吉利知识库导入

- 单测：`pytest tests/test_techstore_knowledge_import.py -q`
- 预览：`GET /api/admin/knowledge-bases/techstore-preview?source=fixture`
- 导入：知识库页按钮，或 `python scripts/import_techstore_knowledge.py`
