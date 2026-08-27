#!/usr/bin/env python3
"""软删 Wiki 编辑台中与 GEOweb 官方 Wiki 无对应 slug 的 wiki_mdx（含误入的长文/Theme 包）。"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.article import Article
from app.services.admin.wiki_import import is_geoweb_aligned_wiki_record, load_official_geoweb_wiki_slugs
from app.services.geoflow.wiki_types import WIKI_CONTENT_FORMAT

logger = get_logger("geoflow.scripts.cleanup_wiki_official_only")


def log(msg: str) -> None:
    print(f"[cleanup-wiki-official] {msg}", flush=True)


async def main() -> int:
    official_slugs = load_official_geoweb_wiki_slugs()
    trashed = 0
    kept = 0
    now = datetime.now(UTC).replace(tzinfo=None)
    async with async_session_factory() as db:
        rows = (await db.execute(select(Article).where(Article.deleted_at.is_(None)))).scalars().all()
        for article in rows:
            if (article.content_format or "") != WIKI_CONTENT_FORMAT:
                continue
            if is_geoweb_aligned_wiki_record(
                content_format=article.content_format,
                slug=article.slug or "",
                wiki_meta=article.wiki_meta if isinstance(article.wiki_meta, dict) else {},
                official_slugs=official_slugs,
            ):
                kept += 1
                continue
            article.deleted_at = now
            article.status = "trashed" if article.status != "trashed" else article.status
            trashed += 1
            log(f"trash id={article.id} slug={article.slug} title={(article.title or '')[:40]}")
        await db.commit()

    log(f"done official_slugs={len(official_slugs)} kept={kept} trashed={trashed}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
