#!/usr/bin/env python3
"""端到端验证：GEOFlow GwebWikiPublisher → Gweb /api/wiki/sync → 公网页面可访问。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.material import Author, Category
from app.services.geoflow.distribution_orchestrator import DistributionOrchestrator

SLUG = "geoflow-e2e-probe"
ROUTE_PREFIX = "glossary"
PROBE_TITLE = "GEOFlow 通路探针"


def log(msg: str) -> None:
    print(f"[gweb-e2e] {msg}", flush=True)


def http_get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


async def ensure_gweb_wiki_channel(db) -> DistributionChannel:
    channel = (
        await db.execute(
            select(DistributionChannel).where(
                DistributionChannel.channel_type == "gweb_wiki",
                DistributionChannel.status == "active",
            )
        )
    ).scalar_one_or_none()

    settings = get_settings()
    if channel:
        log(f"复用 gweb_wiki 渠道 id={channel.id}")
        return channel

    channel = DistributionChannel(
        name="Gweb Wiki 本地",
        channel_type="gweb_wiki",
        status="active",
        config_json={
            "domain": "localhost",
            "endpoint_url": settings.gweb_base_url.rstrip("/"),
            "gweb_base_url": settings.gweb_base_url.rstrip("/"),
            "gweb_sync_secret": settings.gweb_revalidate_secret,
            "gweb_timeout_seconds": 30,
        },
    )
    db.add(channel)
    await db.flush()
    log(f"创建 gweb_wiki 渠道 id={channel.id}")
    return channel


async def create_probe_article(db) -> Article:
    category_id = (await db.execute(select(Category.id).limit(1))).scalar_one()
    author_id = (await db.execute(select(Author.id).limit(1))).scalar_one()

    wiki_meta = {
        "title": PROBE_TITLE,
        "type": "glossary",
        "quick_answer": "端到端探针页：验证 GEOFlow 发布后可经 Gweb 公网访问。",
        "tags": ["GEOFlow", "探针", "E2E"],
        "related": ["topics/geoflow", "guides/geoflow-wiki-publishing", "concepts/shen-dun-battery"],
        "schema_type": "TechArticle",
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "faq": [
            {"q": "本页如何产生？", "a": "由 verify-gweb-e2e.py 经 DistributionOrchestrator 同步写入。"},
            {"q": "通路是否正常？", "a": "若可访问本页且 distribution 状态为 published，则端到端畅通。"},
        ],
    }

    content = """## 定义

本页为 **GEOFlow → Gweb** 端到端通路验证探针，由分发编排器经 `GwebWikiPublisher` 写入。

## 验证项

| 环节 | 期望 |
|:---|:---|
| GEOFlow 配置 | GWEB_SYNC_ENABLED=true |
| 鉴权 | GWEB_REVALIDATE_SECRET 与 Gweb 一致 |
| 同步 API | POST /api/wiki/sync 返回 200 |
| 公网展现 | GET /glossary/geoflow-e2e-probe 返回 200 |

## 相关

- [GEOFlow 内容发布](/topics/geoflow)
- [Wiki 发布指南](/guides/geoflow-wiki-publishing)
- [神盾电池安全系统](/concepts/shen-dun-battery)
"""

    article = Article(
        title=PROBE_TITLE,
        slug=SLUG,
        excerpt=wiki_meta["quick_answer"],
        content=content,
        category_id=category_id,
        author_id=author_id,
        content_format="wiki_mdx",
        wiki_meta=wiki_meta,
        status="published",
        review_status="auto_approved",
        eval_status="passed",
        published_at=datetime.now(UTC).replace(tzinfo=None),
        is_ai_generated=0,
    )
    db.add(article)
    await db.flush()
    log(f"创建探针文章 id={article.id} slug={SLUG}")
    return article


async def run_e2e() -> int:
    settings = get_settings()
    log(f"GWEB_BASE_URL={settings.gweb_base_url}")
    log(f"GWEB_SYNC_ENABLED={settings.gweb_sync_enabled}")

    if not settings.gweb_sync_enabled:
        log("FAIL: GWEB_SYNC_ENABLED 未开启")
        return 1
    if not settings.gweb_revalidate_secret:
        log("FAIL: GWEB_REVALIDATE_SECRET 未配置")
        return 1

    gweb_health_url = f"{settings.gweb_base_url.rstrip('/')}/api/health"
    code, body = http_get(gweb_health_url)
    if code != 200 or "gweb" not in body:
        log(f"FAIL: Gweb 不可达 {gweb_health_url} status={code}")
        return 1
    log(f"Gweb 健康检查 OK ({gweb_health_url})")

    async with async_session_factory() as db:
        await ensure_gweb_wiki_channel(db)
        existing = (
            await db.execute(select(Article).where(Article.slug == SLUG))
        ).scalar_one_or_none()
        if existing:
            article = existing
            log(f"复用探针文章 id={article.id} slug={SLUG}")
        else:
            article = await create_probe_article(db)
        await db.commit()
        article_id = article.id

    async with async_session_factory() as db:
        orchestrator = DistributionOrchestrator(db)
        await orchestrator.distribute_article(article_id)
        await db.commit()
        dist = (
            await db.execute(
                select(ArticleDistribution)
                .where(ArticleDistribution.article_id == article_id)
                .order_by(ArticleDistribution.id.desc())
            )
        ).scalar_one()

    log(f"分发结果 status={dist.status} remote_url={dist.remote_url!r} error={dist.error_message!r}")
    if dist.status != "published":
        log("FAIL: article_distributions 未 published")
        return 1

    page_url = f"{settings.gweb_base_url.rstrip('/')}/{ROUTE_PREFIX}/{SLUG}"
    for attempt in range(1, 8):
        code, html = http_get(page_url)
        if code == 200 and PROBE_TITLE in html:
            log(f"OK  公网页面可访问 {page_url}")
            log(json.dumps({"article_id": article_id, "distribution_id": dist.id, "url": page_url}, ensure_ascii=False))
            return 0
        log(f"等待页面就绪 ({attempt}/7) status={code}")
        time.sleep(2)

    log(f"FAIL: 页面不可访问或未包含标题 {page_url}")
    return 1


def main() -> int:
    return asyncio.run(run_e2e())


if __name__ == "__main__":
    sys.exit(main())
