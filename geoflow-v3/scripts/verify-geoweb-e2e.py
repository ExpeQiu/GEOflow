#!/usr/bin/env python3
"""端到端验证：GEOFlow GeowebPublisher → GEOweb /api/geoflow/sync → /articles 可访问。"""

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

SLUG = "geoflow-geoweb-e2e-probe"
PROBE_TITLE = "GEOFlow → GEOweb 通路探针"


def log(msg: str) -> None:
    print(f"[geoweb-e2e] {msg}", flush=True)


def http_get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


async def ensure_geoweb_channel(db) -> DistributionChannel:
    channel = (
        await db.execute(
            select(DistributionChannel).where(
                DistributionChannel.channel_type == "geoweb",
                DistributionChannel.status == "active",
            )
        )
    ).scalar_one_or_none()

    settings = get_settings()
    if channel:
        log(f"复用 geoweb 渠道 id={channel.id}")
        return channel

    base = (settings.geoweb_base_url or "").rstrip("/")
    channel = DistributionChannel(
        name="GEOweb 本地",
        channel_type="geoweb",
        status="active",
        config_json={
            "domain": "127.0.0.1",
            "endpoint_url": base,
            "geoweb_base_url": base,
            "geoweb_sync_token": settings.geoweb_sync_token,
            "geoweb_timeout_seconds": 30,
            "default_page_type": "article",
        },
    )
    db.add(channel)
    await db.flush()
    log(f"创建 geoweb 渠道 id={channel.id}")
    return channel


async def create_probe_article(db) -> Article:
    category_id = (await db.execute(select(Category.id).limit(1))).scalar_one()
    author_id = (await db.execute(select(Author.id).limit(1))).scalar_one()

    content = """## 定义

本页为 **GEOFlow → GEOweb** 端到端通路验证探针。

## 验证项

| 环节 | 期望 |
|:---|:---|
| GEOFlow 配置 | GEOWEB_SYNC_ENABLED=true |
| 鉴权 | GEOWEB_SYNC_TOKEN 与 GEOweb GEOFLOW_SYNC_TOKEN 一致 |
| 同步 API | POST /api/geoflow/sync 返回 200 |
| 展现 | GET /articles/geoflow-geoweb-e2e-probe 返回 200 |
"""

    article = Article(
        title=PROBE_TITLE,
        slug=SLUG,
        excerpt="端到端探针：验证发布后可经 GEOweb /articles 访问。",
        content=content,
        category_id=category_id,
        author_id=author_id,
        content_format="article",
        original_keyword="GEOFlow GEOweb 发布验证",
        wiki_meta={
            "domain": "adas",
            "core_takeaway": "GEOFlow 发布可同步到 GEOweb /articles",
            "quick_answer": "通路探针页",
            "target_query": "GEOFlow 如何发布到 GEOweb",
        },
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
    base = (settings.geoweb_base_url or "").rstrip("/")
    log(f"GEOWEB_BASE_URL={base}")
    log(f"GEOWEB_SYNC_ENABLED={settings.geoweb_sync_enabled}")

    if not settings.geoweb_sync_enabled:
        log("FAIL: GEOWEB_SYNC_ENABLED 未开启")
        return 1
    if not settings.geoweb_sync_token:
        log("FAIL: GEOWEB_SYNC_TOKEN 未配置")
        return 1
    if not base:
        log("FAIL: GEOWEB_BASE_URL 未配置")
        return 1

    home_code, _ = http_get(f"{base}/")
    if home_code != 200:
        log(f"FAIL: GEOweb 不可达 {base}/ status={home_code}")
        return 1
    log("GEOweb 首页 OK")

    async with async_session_factory() as db:
        await ensure_geoweb_channel(db)
        existing = (
            await db.execute(select(Article).where(Article.slug == SLUG))
        ).scalar_one_or_none()
        if existing:
            article = existing
            log(f"复用探针文章 id={article.id}")
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

    page_url = f"{base}/articles/{SLUG}"
    for attempt in range(1, 8):
        code, html = http_get(page_url)
        if code == 200 and PROBE_TITLE in html:
            log(f"OK 页面可访问 {page_url}")
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
