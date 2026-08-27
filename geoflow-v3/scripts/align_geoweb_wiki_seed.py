#!/usr/bin/env python3
"""从 GEOweb 官方 Wiki seed 对齐 GEOFlow Wiki 编辑台（不含 geoflow 管线页与 /articles 长文）。"""

from __future__ import annotations

import asyncio
import os
import sys

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.services.admin.wiki_editor_service import import_geoweb_wiki_pages

logger = get_logger("geoflow.scripts.align_geoweb_wiki")


def log(msg: str) -> None:
    print(f"[align-geoweb-wiki] {msg}", flush=True)


async def main() -> int:
    wiki_dir = (os.environ.get("GEOWEB_WIKI_DIR") or "").strip() or None
    async with async_session_factory() as db:
        try:
            payload = await import_geoweb_wiki_pages(
                db,
                wiki_dir=wiki_dir,
                include_smoke=False,
                official_only=True,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            log(f"FAIL: {exc}")
            return 1

    imp = payload.get("import") or {}
    log(
        "done "
        f"created={imp.get('created', 0)} "
        f"updated={imp.get('updated', 0)} "
        f"official={imp.get('official_count', 0)} "
        f"geoflow_skipped={imp.get('geoflow_skipped', 0)} "
        f"conflict={imp.get('conflict', 0)} "
        f"dir={imp.get('wiki_dir')}"
    )
    stats = payload.get("stats") or {}
    log(f"wiki_panel total={stats.get('total')} visible={stats.get('visible')} synced={stats.get('synced')}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
