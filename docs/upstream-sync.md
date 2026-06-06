# GEOFlow 上游同步 SOP

## 分支结构

- `main` — 个性化开发主线
- `vendor-main` — 跟踪 `upstream/main`
- `chore/sync-upstream-YYYYMMDD` — 同步整合分支

## 同步步骤

```bash
git fetch upstream
git switch vendor-main
git merge --ff-only upstream/main
git switch main
git switch -c chore/sync-upstream-$(date +%Y%m%d)
git merge vendor-main
# 解决冲突 → composer test → 合回 main
```

## 定制隔离

GEO 评估相关代码位于 `app/Services/GeoEval/`、`config/geo_eval.php`，与上游核心文件解耦，降低同步冲突成本。
