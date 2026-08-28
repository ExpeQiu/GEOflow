#!/usr/bin/env python3
"""软删 Wiki 编辑台中非 Wiki 内容（分发长文、探针、无官方 slug 的污染页）。"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.article import Article
from app.services.admin.wiki_import import load_official_geoweb_wiki_slugs
from app.services.geoflow.wiki_types import WIKI_CONTENT_FORMAT, is_editable_wiki_panel_record

logger = get_logger("geoflow.scripts.cleanup_wiki_official_only")


def log(msg: str) -> None:
    print(f"[cleanup-wiki-official] {msg}", flush=True)


async def main() -> int:
    settings = get_settings()
    official_slugs = load_official_geoweb_wiki_slugs()
    tech_brand_mode = bool(settings.geoflow_tech_brand_mode)
    trashed = 0
    kept = 0
    now = datetime.now(UTC).replace(tzinfo=None)
    async with async_session_factory() as db:
        rows = (await db.execute(select(Article).where(Article.deleted_at.is_(None)))).scalars().all()
        for article in rows:
            if (article.content_format or "") != WIKI_CONTENT_FORMAT:
                continue
            meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
            if is_editable_wiki_panel_record(
                content_format=article.content_format,
                theme_id=article.theme_id,
                slug=article.slug or "",
                title=article.title or "",
                wiki_meta=meta,
                official_slugs=official_slugs,
                tech_brand_mode=tech_brand_mode,
            ):
                kept += 1
                continue
            article.deleted_at = now
            article.status = "trashed"
            trashed += 1
            log(f"trash id={article.id} slug={article.slug} title={(article.title or '')[:40]}")
        await db.commit()

    log(
        f"done tech_brand_mode={tech_brand_mode} official_slugs={len(official_slugs)} kept={kept} trashed={trashed}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
