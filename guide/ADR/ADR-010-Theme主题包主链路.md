# ADR-010：Theme 主题包主链路

- 状态：Accepted
- 日期：2026-08-14

## 决策

以 **Theme（主题包）** 作为贯穿 L1 策略 → L2 生产/门禁 → L3 分发 → GEOweb 的一等公民。

场景缺口默认生成 **草稿 Theme**，人工确认后才创建 Task 与 remediation；不再默认「一键直接建 Task」。

## 产品心智（与「监控问题库」分界）

主链路：**问题库→探针检测→找差距→挖主题→内容生产→绩优门禁→运营分发/索引/监控→再扫**。

| 对象 | 用途 |
|------|------|
| **监控问题库** | 构建探针，测品牌/技术 IP 排名；偏关键词、可复测 |
| **Theme** | 针对差距场景发散；挖 AI 思考路径与信源；用户导向、长尾；交给内容生产一组稿 |

用户场景展开优先覆盖**思考链与关键词组合多样性**，而非仅用户原问题的字面覆盖。

详细指引见知识库：`技术品牌战术/GEO/系统设计/GEO主链路结构化指引.md`。  
三层探针口径见：`技术品牌战术/GEO/系统设计/GEO三层探针体系方案.md`。

## 状态机

`draft → confirmed → producing → gate_passed → distributing → published → measuring → completed`

## 复合包默认规格

`topic` hub + `concept` + `compare` + `guide`（+ 可选 `article`），对齐 GEOweb content-schema。

## 边界

| 系统 | 职责 |
|------|------|
| GEOFlow | Theme CRUD、门禁聚合、Task/Remediation 关联 |
| GEOweb | 单页 sync + `sync-pack`；`geo_theme_id` frontmatter |
| Gweb | 不在链路 |

## 兼容

`POST .../scenes/{id}/create-task?legacy_direct_task=true` 保留旧行为一个版本（弃用）。

## 主题挖掘约定（监控题 ≠ 生产题）

- 缺口/Wiki 来源 Theme 默认 `gate_mode=hard`（人工可改 soft）
- `target_queries` 使用挖掘出的用户向长尾 Query，**禁止**把探针 `unsupported_sample` 原样当生产标题
- 探针题进入 `meta.mining.probe_evidence`；思考链/信源进入 `thinking_digest` / `source_hints`
- UI：主题包详情看「挖掘摘要」后再确认；可 `spawn-candidate` 另存备选草稿

## 后果

- 运营叙事以 Theme 漏斗为主；L1→L2 交接物是 Theme，不是监控题本身
- 硬门禁下整包未过不进入分发
- 再扫完成后 Theme 自动 `measuring → completed`
- 日志键：`theme_id` / `scene_id` / `task_id` / `eval_status` / `gate_mode`
