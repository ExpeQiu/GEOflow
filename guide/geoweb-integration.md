# GEOweb 集成（GEOFlow 唯一官方发布站）

> Gweb（`/Volumes/Lexar/git/08 Gene/Gweb`）是**另一个项目的前台**，与 GEOFlow 分发无关。  
> GEOFlow 只对接 **GEOweb**（`/Volumes/Lexar/git/03T/GEOweb`）。

## 分工

| 系统 | 角色 |
|:---|:---|
| **GEOFlow** | 内容生产、审核、发布、分发编排 |
| **GEOweb** | 官方技术发布站（`/articles` + Wiki） |
| **Gweb** | 独立项目前台（不在本链路） |

## 数据流

```
GEOFlow Article 发布
  → channel_type=geoweb
  → GeowebPublisher
  → POST {GEOWEB_BASE_URL}/api/geoflow/sync
  → /articles 或 Wiki 路由
```

## 环境变量

```env
GEOWEB_BASE_URL=http://127.0.0.1:3070
GEOWEB_SYNC_TOKEN=shared-with-geoweb
GEOWEB_SYNC_ENABLED=true
```

GEOweb：`GEOFLOW_SYNC_TOKEN` 必须与上列 Token 一致。

## 存量清理

```bash
cd geoflow-v3/backend
PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py --dry-run
PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py          # 转为 geoweb
# 或
PYTHONPATH=. python ../scripts/migrate_gweb_channels_to_geoweb.py --delete # 直接删除
```

## 渠道类型

| 类型 | 用途 |
|:---|:---|
| `geoweb` | 官方发布站（默认，技术品牌模式） |
| `wordpress_rest` | 外部分发 |
| `generic_http_api` | 外部分发 |
| `geoflow_agent` | Agent 站点 |

`gweb_wiki` **已删除**，不可新建。

## 契约

见 GEOweb `guide/geoflow-sync.md`。e2e：`scripts/verify-geoweb-e2e.py`。
