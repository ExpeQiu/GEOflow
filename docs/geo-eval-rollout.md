# GEO 评估灰度与回滚

## 灰度开启

1. `GEO_EVAL_ENABLED=true`
2. `GEO_EVAL_GATE_ENABLED=true`（仅影响**任务自动发布**）
3. `GEO_EVAL_GATE_ROLLOUT_PERCENT=10`（10% 文章走门禁）

评估任务在 `GEO_EVAL_ENABLED=true` 时即会执行，与门禁开关无关。

## 手动发布

后台文章编辑/审核中手动改为「已发布」**不受** `canPublish()` 限制（设计选择）。

## 验证

```bash
./scripts/verify.sh geo-eval
docker compose exec -T app php artisan test --filter=GeoEval
```

## 回滚

1. `GEO_EVAL_GATE_ENABLED=false` 或 `GEO_EVAL_ENABLED=false`
2. `php artisan config:clear`
3. 失败文章批量：`UPDATE articles SET eval_status='skipped' WHERE eval_status='failed';`

## 采纳聚合与告警

```bash
php artisan geo:aggregate-adoption-metrics --days=30
php artisan geo:check-adoption-alerts
php artisan geo:market-scan --type=weekly
```
