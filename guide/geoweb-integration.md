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
GEOFlow 生产-分发（content_format=article）
  → GeowebPublisher geoflow_lane=distribution
  → POST /api/geoflow/sync type=article
  → GEOweb /articles

GEOFlow Wiki 定稿（content_format=wiki_mdx）
  → GeowebPublisher geoflow_lane=wiki
  → POST /api/geoflow/sync type=concept|guide|…
  → GEOweb Wiki 路由
```

### Theme 复合主题包

```
Theme confirm → Task 生产多页（topic/concept/compare/guide…）
  → geo-eval 门禁聚合
  → 先 sync 子页，后 sync topic hub（related 指向子页）
  → 或一次 POST /api/geoflow/sync-pack { theme_id, pages[] }
```

顺序：**子页先于 hub**。payload 带 `geo_theme_id`。

## 环境变量

```env
GEOWEB_BASE_URL=http://127.0.0.1:3070
GEOWEB_SYNC_TOKEN=shared-with-geoweb
GEOWEB_SYNC_ENABLED=true
```

Postgres 与 Techstore 共用实例、分库，见 [ADR-017](./ADR/ADR-017-共享PostgreSQL实例.md)。

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

## 技术 Wiki 与 GEOFlow 知识库（规划）

当前 Wiki 由 Article / Theme 发布写入 MD。后续：

1. **轻量编辑台（Wave 1 已落地）**：GEOFlow Admin `/operations/wiki` 定稿与一键 sync，见 [ADR-011](./ADR/ADR-011-GEOweb-Wiki轻量编辑台.md)
2. 生产语料来自 GEOFlow **KnowledgeBase**，生成草稿后再进编辑台（Wave 2）
3. **Techstore 导入（ADR-014）**：只读灌入知识库 + 技术 IP，不把地图树当 Wiki 真源

不把 Techstore 知识地图树当成 Wiki 真源：地图是运营结构，Wiki 是 GEO 可引用文本。

## 契约

见 GEOweb `guide/geoflow-sync.md`。e2e：`scripts/verify-geoweb-e2e.py`。
