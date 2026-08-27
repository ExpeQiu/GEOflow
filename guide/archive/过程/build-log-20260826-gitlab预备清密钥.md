# 构建日志：GitLab 预备清密钥

日期：2026-08-26

## 做了什么

- 从 Git 索引移除 `geoflow-v3/.env.local`（本地文件保留，不入库）
- `.gitignore` 补 `.env.*` / `*.bak` / `*.pid` / `celerybeat-schedule*`
- 重写相对 `origin/feat/geoflow-geo-upgrade` 未推送的提交，去掉其中的 `.env.local` 与 celerybeat 运行时文件

## 仍须人工完成

- 轮换 DeepSeek API Key：控制台无开放创 Key API，需在 https://platform.deepseek.com/api_keys 新建并吊销旧 key，再写入 `geoflow-v3/.env.local`
- GitHub `feat` 历史中的旧 `.env.local` 不会因库密码轮换而消失；Key 必须作废

## 已执行（2026-08-26 续）

- 云库角色 `miniprogram@111.230.58.40:5433` 已 `ALTER USER`；旧口令登录已拒绝
- 已回写本地（均 gitignore）：GEOFlow `.env`/`.env.local`、Techstore `.env.local`、GEOweb `.env`、Gweb `.env.local`、weixin2 `.env.wxcloud`

