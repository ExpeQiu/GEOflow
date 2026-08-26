# 构建日志：GitLab 预备清密钥

日期：2026-08-26

## 做了什么

- 从 Git 索引移除 `geoflow-v3/.env.local`（本地文件保留，不入库）
- `.gitignore` 补 `.env.*` / `*.bak` / `*.pid` / `celerybeat-schedule*`
- 重写相对 `origin/feat/geoflow-geo-upgrade` 未推送的提交，去掉其中的 `.env.local` 与 celerybeat 运行时文件

## 仍须人工完成

- 轮换 DeepSeek API Key（GitHub `feat` 历史里已出现过该文件）
- 轮换 `TECHSTORE_DATABASE_URL` 对应库密码
- **不要** `git push --force` 到 `main`；GitHub `feat` 上旧提交仍含该文件，密钥以轮换为准
