#!/usr/bin/env python3
"""软删 GEOFlow 长文章表中标题重复的记录（保留最新 id）。"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.article import Article
from app.services.geoflow.wiki_types import (
    WIKI_CONTENT_FORMAT,
    infer_wiki_page_type_from_article,
    is_distribution_article,
)

logger = get_logger("geoflow.scripts.dedupe_articles")

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
TEST_TITLE = re.compile(r"内容生产流程测试")


def log(msg: str) -> None:
    print(f"[dedupe-articles] {msg}", flush=True)


def article_score(article: Article) -> tuple:
    meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
    synced = str(meta.get("last_synced_at") or "")
    updated = article.updated_at.isoformat() if article.updated_at else ""
    return (synced, updated, article.id or 0)


async def main() -> int:
    trashed = 0
    kept = 0
    reasons: Counter[str] = Counter()
    removed_slugs: list[str] = []
    kept_slugs: list[str] = []
    now = datetime.now(UTC).replace(tzinfo=None)

    async with async_session_factory() as db:
        rows = (
            await db.execute(select(Article).where(Article.deleted_at.is_(None)))
        ).scalars().all()

        distribution: list[Article] = []
        for article in rows:
            if not is_distribution_article(
                content_format=article.content_format,
                slug=article.slug or "",
                title=article.title or "",
                wiki_meta=article.wiki_meta if isinstance(article.wiki_meta, dict) else {},
            ):
                continue
            distribution.append(article)

        by_title: dict[str, list[Article]] = defaultdict(list)
        for article in distribution:
            by_title[(article.title or "").strip() or (article.slug or "")].append(article)

        keep_ids: set[int] = set()
        for title, group in by_title.items():
            if TEST_TITLE.search(title):
                for article in group:
                    article.deleted_at = now
                    article.status = "trashed"
                    trashed += 1
                    reasons["test"] += 1
                    removed_slugs.append(article.slug or "")
                    log(f"trash test id={article.id} slug={article.slug}")
                continue

            best = max(group, key=article_score)
            keep_ids.add(best.id)
            kept_slugs.append(best.slug or "")
            for article in group:
                if article.id == best.id:
                    kept += 1
                    continue
                article.deleted_at = now
                article.status = "trashed"
                trashed += 1
                reasons["dup_title"] += 1
                removed_slugs.append(article.slug or "")
                log(f"trash dup id={article.id} slug={article.slug} title={(article.title or '')[:40]}")

        # Wiki 页型误留在 article 表
        for article in rows:
            if article.id in keep_ids or article.deleted_at:
                continue
            if (article.content_format or "article") != "article":
                continue
            wiki_type = infer_wiki_page_type_from_article(
                slug=article.slug or "",
                title=article.title or "",
                wiki_meta=article.wiki_meta if isinstance(article.wiki_meta, dict) else {},
            )
            if wiki_type:
                meta = dict(article.wiki_meta) if isinstance(article.wiki_meta, dict) else {}
                meta["type"] = wiki_type
                meta["wiki_page_type"] = wiki_type
                meta.setdefault("geoflow_lane", "wiki")
                article.content_format = WIKI_CONTENT_FORMAT
                article.wiki_meta = meta
                reasons["migrated_wiki"] += 1
                log(f"migrate wiki id={article.id} slug={article.slug} type={wiki_type}")

        await db.commit()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "ts": stamp,
        "kept": kept,
        "trashed": trashed,
        "reasons": dict(reasons),
        "kept_slugs": sorted(set(kept_slugs)),
        "removed_slugs": sorted(set(removed_slugs)),
    }
    report_path = LOG_DIR / f"dedupe-articles-{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"done kept={kept} trashed={trashed} reasons={dict(reasons)} report={report_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
