#!/usr/bin/env python3
"""将误写入长文章表的 Wiki 页（concept/guide/compare 等）迁回 wiki_mdx。"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.article import Article
from app.services.geoflow.wiki_types import (
    WIKI_CONTENT_FORMAT,
    infer_wiki_page_type_from_article,
    is_distribution_article,
)

logger = get_logger("geoflow.scripts.cleanup_article_wiki_junk")


def log(msg: str) -> None:
    print(f"[cleanup-article-wiki] {msg}", flush=True)


async def main() -> int:
    migrated = 0
    skipped = 0
    async with async_session_factory() as db:
        rows = (await db.execute(select(Article).where(Article.deleted_at.is_(None)))).scalars().all()
        for article in rows:
            if (article.content_format or "article") != "article":
                continue
            if is_distribution_article(
                content_format=article.content_format,
                slug=article.slug or "",
                title=article.title or "",
                wiki_meta=article.wiki_meta if isinstance(article.wiki_meta, dict) else {},
            ):
                continue
            wiki_type = infer_wiki_page_type_from_article(
                slug=article.slug or "",
                title=article.title or "",
                wiki_meta=article.wiki_meta if isinstance(article.wiki_meta, dict) else {},
            )
            if not wiki_type:
                skipped += 1
                continue
            meta = dict(article.wiki_meta) if isinstance(article.wiki_meta, dict) else {}
            meta["type"] = wiki_type
            meta["wiki_page_type"] = wiki_type
            meta.setdefault("geoflow_lane", "wiki")
            meta.setdefault("slug", article.slug)
            article.content_format = WIKI_CONTENT_FORMAT
            article.wiki_meta = meta
            migrated += 1
            log(f"migrate id={article.id} slug={article.slug} -> wiki_mdx/{wiki_type}")
        await db.commit()

    log(f"done migrated={migrated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
