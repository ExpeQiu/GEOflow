# Docker 开发环境 + GEO 策略模块

GEO 能力在 GEOFlow 进程内运行，**无需**单独启动 GEO-OS。

## 快速升级

```bash
./scripts/docker-upgrade.sh
```

## `.env` 关键项

```env
GEO_EVAL_ENABLED=true
GEO_EVAL_GATE_ENABLED=false
```

- `GEO_EVAL_ENABLED=true`：开启评估任务与后台模块。
- `GEO_EVAL_GATE_ENABLED=true`：发布前门禁（建议灰度 `GEO_EVAL_GATE_ROLLOUT_PERCENT`）。

修改后：

```bash
docker compose exec app php artisan config:clear
docker compose restart queue app
```

## 验证

```bash
./scripts/verify.sh docker
./scripts/verify.sh geo-eval
```
