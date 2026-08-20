# ADR-012：三层探针 `scheme` / `tracks` / `reasoning_grade`

- 状态：Accepted（P0/P1/P2 已落地）
- 日期：2026-08-20
- 相关：[ADR-010 Theme](./ADR-010-Theme主题包主链路.md)、知识库 `GEO三层探针体系方案.md`

## 决策

探针结果显式标注采样方案与切面，与 `engine`（api/llm/corpus/cend_browser）解绑。

| 字段 | 取值 | 含义 |
|------|------|------|
| `scheme` | `open_api` / `framework_api` / `citation_grounded` / `cend_sample` | 组合验证方案 |
| `tracks` | `A` 框架 / `B` 引用 / `C` 回答 | 本条实际采到的层 |
| `reasoning_grade` | `raw` / `summary` / `none` | 思维链是否明文真源 |
| `metric_kind` | `open_api` / `framework_sample` / `cend_sample` / `citation_sample` / `mixed` | KPI 隔离 |
| `framework` | JSON 六类框架 | 仅 A 轨消费 |

## 硬约束

- **禁止**用 `framework_api` / `cend_sample` / `citation_grounded` 覆盖或加权改写 `visibility_open_api`。
- 北极星只计：`engine=api` 且 `scheme=open_api`（缺列视同 open_api），并排除 `metric_kind ∈ {cend_sample, framework_sample, citation_sample}`。
- 缺 A 能力的模型不得把摘要标成 `reasoning_grade=raw`。C 端 UI 思考默认 `summary`。
- 主题挖掘只消费 `reasoning_grade=raw`；禁止用 `snippet` 冒充思维链。
- GEOweb 主机计入 `official_domains`（`match_type=domain_official`）；第三方百科才是 `domain_wiki`。

## 方案路由

| scheme | 进 daily | 默认 tracks | 连接器 |
|--------|----------|-------------|--------|
| `open_api` | 是 | `[C]` | 豆包/DeepSeek Chat，不开思考 |
| `framework_api` | 否，独立扫描 | `[A,C]` | DeepSeek（+可选豆包）开思考 |
| `cend_sample` | 否 | `[B,C]` | Playwright C 端 |
| `citation_grounded` | 否，独立扫描 | `[B,C]` | 豆包/Kimi API 抽 URL；Mock 可跑 |

## 交叉判定（P2）

| 标志 | 含义 |
|------|------|
| `mention_no_ours` | C 提及品牌但 B 无我方域名 → 信源缺口 |
| `framework_not_in_answer` | A 维度未出现在 C 答文 → 内容形态缺口 |
| `ours_cited` | 提及且引用我方域名 |
| `gold` | 同题具备 A∩B∩C 且我方被引 |

API：`POST /strategy/citation/scan`、`GET /strategy/cross-track`。

## 后果

- `ProbeOutcome` 与 `geo_monitor_probe_results` 增列；插入失败回退旧 SQL。
- 日志键：`scheme` / `tracks` / `reasoning_grade` / `run_id` / `question_id`。
