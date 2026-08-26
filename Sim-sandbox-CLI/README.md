# Sim-sandbox-CLI

独立 **探针真值标定仿真沙箱**（归档外挂）。

> **归档**：主栈不安装。主栈已自建 `answer_parser`；本仓仅夹具评测与 `calibrate` 辅轨。见 [guide/cli-plugins.md](../guide/cli-plugins.md)。
## 安装

```bash
cd Sim-sandbox-CLI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# 或直接 ./verify.sh
```

## 命令面

```bash
simsb --version

# L1：解析单条答文
simsb parse --brands 吉利 --competitors 比亚迪,小鹏 \
  --text $'1. 比亚迪\n2. 吉利\n3. 小鹏'

# L1：夹具评测（list_order 准确率门槛默认 0.8）
simsb eval --demo
simsb eval ./fixtures/rank --format table

# L3：偏移对照（只出建议，不改写主 KPI）
simsb calibrate --demo
simsb calibrate --open-api ./my_api.jsonl --gold ./my_gold.jsonl
```

## 设计要点

| 能力 | 入口 | metric_kind | 说明 |
|------|------|-------------|------|
| 答文解析 | `simsb parse` | — | list_order → first_mention；URL→L0/L1 |
| 夹具评测 | `simsb eval` | `fixture` | 离线 CI，不连 API |
| 偏移报告 | `simsb calibrate` | `bias_report` | 同题对照，旋钮建议 |

原则：**夹具锁解析，金标调旋钮；永不自动覆盖 `visibility_open_api`。**

## Web UI

```bash
./start.sh          # http://127.0.0.1:8765
./stop.sh
```

解析 / 评测 / 金标对照三页，调用同一套 `simsb.core`（不依赖 GEOFlow）。

## 验收

```bash
./verify.sh
```

无外网、无 GEOFlow 即可通过。

## 文档

- [guide/architecture.md](./guide/architecture.md)
- [guide/geoflow-contract.md](./guide/geoflow-contract.md)
