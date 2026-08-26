"""缺口场景 → Theme 草稿（ADR-010）。直接建 Task 已移除。"""

import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geoeval.theme_service import create_theme_from_scene

logger = logging.getLogger(__name__)


async def create_task_from_scene_gap(
    db: AsyncSession,
    scene_id: int,
    *,
    legacy_direct_task: bool = False,
) -> dict:
    """只创建 Theme 草稿。legacy_direct_task=true 返回 410。"""
    if legacy_direct_task:
        raise HTTPException(status_code=410, detail="legacy_direct_task_removed_use_theme_draft")

    result = await create_theme_from_scene(db, scene_id)
    logger.info(
        "gap_theme_draft_created theme_id=%s scene_id=%s",
        result.get("theme", {}).get("id"),
        scene_id,
    )
    return {
        "mode": "theme_draft",
        "theme_id": result["theme"]["id"],
        "theme": result["theme"],
        "gap": result.get("gap"),
        "scene_id": scene_id,
        "deprecated_direct_task": False,
        "next_step": "确认主题规格后调用 POST /api/admin/themes/{id}/confirm",
    }
