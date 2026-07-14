# 架构说明

## 目标

在独立仓库验证探针 **仿真沙箱 L1（夹具评测）** 与 **L3（金标偏移对照）** 的 CLI UX、JSON 契约与离线路径。**不修改 GEOFlow。**

## 组件

```
simsb CLI (Click)                 simsb Web (FastAPI + static)
    │                                  │
    ├─ parse                      /api/parse
    ├─ eval                       /api/eval
    └─ calibrate                  /api/calibrate
            │                          │
            └──── core/* 共享 ─────────┘
                    │
                    ├─ fixtures/rank|citation
                    └─ config/calibration.yml
```

Web：`./start.sh` → http://127.0.0.1:8765 ；`./stop.sh` 停服。

## 三层仿真（分期）

| 层 | 本仓 v0.1 | 说明 |
|----|-----------|------|
| L1 答文回放 | ✅ | 确定性夹具 + 同一 parser |
| L2 策略仿真 | ⏸ | 可选 llm_sim 生成答文后再 parser |
| L3 金标对照 | ✅ 薄实现 | JSONL 对照 → bias_report + suggestions |

## 输出约定

- **stdout**：JSON / table 业务结果（可管道）
- **stderr**：日志与进度
- Exit：`0` 成功；`2` 用法；`1` 评测未过门槛或其他错误

## 边界

本仓 **不** 调用豆包/DeepSeek 生产探针、不写 GEOFlow DB、不驱动 remediation lift。
