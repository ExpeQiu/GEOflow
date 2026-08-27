"""敏感词过滤 — 读取 site_settings.sensitive_words。"""

from __future__ import annotations

import logging
import re

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


async def load_sensitive_words(db: AsyncSession) -> list[str]:
    if not await _table_exists(db, "site_settings"):
        return []
    row = (
        await db.execute(text("SELECT setting_value FROM site_settings WHERE setting_key = 'sensitive_words' LIMIT 1"))
    ).first()
    raw = (row[0] if row else "") or ""
    return [w.strip() for w in raw.splitlines() if w.strip()]


def find_hits(text_blob: str, words: list[str]) -> list[str]:
    if not text_blob or not words:
        return []
    hits: list[str] = []
    for w in words:
        if not w:
            continue
        if re.search(re.escape(w), text_blob, flags=re.IGNORECASE):
            hits.append(w)
    return hits


async def assert_text_clean(db: AsyncSession, *parts: str, context: str = "content") -> None:
    words = await load_sensitive_words(db)
    if not words:
        return
    blob = "\n".join(p for p in parts if p)
    hits = find_hits(blob, words)
    if hits:
        logger.warning("sensitive_words_hit context=%s hits=%s", context, hits[:8])
        raise HTTPException(status_code=422, detail=f"sensitive_words_hit:{','.join(hits[:8])}")
