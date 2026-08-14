"""缺口场景 → Theme 草稿（默认）或 legacy 直接建 Task。"""

import json
import logging

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import Prompt
from app.services.admin.production_service import _table_exists
from app.services.admin.task_form_service import AdminTaskCreateBody, create_admin_task
from app.services.geoeval.scene_gap_analyzer import compute_scene_gap
from app.services.geoeval.theme_service import create_theme_from_scene, resolve_default_geoweb_channel_ids

logger = logging.getLogger(__name__)


async def _load_gap_task_defaults(db: AsyncSession) -> dict:
    defaults = {
        "title_library_id": None,
        "prompt_id": None,
        "ai_model_id": None,
        "knowledge_base_id": None,
    }
    if not await _table_exists(db, "site_settings"):
        return defaults
    key_map = {
        "gap_task_title_library_id": "title_library_id",
        "gap_task_prompt_id": "prompt_id",
        "gap_task_ai_model_id": "ai_model_id",
        "default_knowledge_base_id": "knowledge_base_id",
    }
    rows = (
        await db.execute(
            text(
                """
                SELECT setting_key, setting_value FROM site_settings
                WHERE setting_key IN (
                    'gap_task_title_library_id', 'gap_task_prompt_id',
                    'gap_task_ai_model_id', 'default_knowledge_base_id'
                )
                """
            )
        )
    ).all()
    for key, value in rows:
        field = key_map.get(str(key))
        if field and value:
            try:
                defaults[field] = int(value)
            except (TypeError, ValueError):
                pass
    return defaults


async def _fallback_ids(db: AsyncSession) -> tuple[int, int, int]:
    title_lib = (
        await db.execute(text("SELECT id FROM title_libraries ORDER BY id LIMIT 1"))
    ).scalar_one_or_none()
    prompt = (await db.execute(select(Prompt.id).order_by(Prompt.id).limit(1))).scalar_one_or_none()
    model = (
        await db.execute(text("SELECT id FROM ai_models WHERE status = 'active' ORDER BY id LIMIT 1"))
    ).scalar_one_or_none()
    if not title_lib or not prompt or not model:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "gap_task_defaults_missing",
                "message": "缺少标题库/提示词/模型，请到 内容生产 配置",
                "hint": "/production/materials",
            },
        )
    return int(title_lib), int(prompt), int(model)


async def create_task_from_scene_gap(
    db: AsyncSession,
    scene_id: int,
    *,
    legacy_direct_task: bool = False,
) -> dict:
    """默认创建 Theme 草稿；legacy_direct_task=true 时保持旧行为直接建 Task。"""
    if not legacy_direct_task:
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

    gap = await compute_scene_gap(db, scene_id)
    if gap.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="scene_not_found")

    scene_row = (
        await db.execute(
            text(
                """
                SELECT scene_name, intent, insight_template_id, gap_rate
                FROM geo_monitor_scenes WHERE id = :id
                """
            ),
            {"id": scene_id},
        )
    ).first()
    if not scene_row:
        raise HTTPException(status_code=404, detail="scene_not_found")

    defaults = await _load_gap_task_defaults(db)
    title_lib_id, prompt_id, model_id = await _fallback_ids(db)
    title_lib_id = defaults.get("title_library_id") or title_lib_id
    prompt_id = defaults.get("prompt_id") or prompt_id
    model_id = defaults.get("ai_model_id") or model_id
    kb_id = defaults.get("knowledge_base_id")

    channel_ids = await resolve_default_geoweb_channel_ids(db)
    if not channel_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "geoweb_channel_missing",
                "message": "缺少活跃 GEOweb 分发渠道",
                "hint": "/operations/distribution",
            },
        )

    task_name = f"[缺口补缺] {scene_row[0]} — {scene_row[1] or '场景'}"
    body = AdminTaskCreateBody(
        task_name=task_name[:200],
        title_library_id=title_lib_id,
        prompt_id=prompt_id,
        ai_model_id=model_id,
        knowledge_base_id=kb_id,
        insight_template_id=int(scene_row[2]) if scene_row[2] else None,
        content_format="wiki_mdx",
        publish_scope="distribution_only",
        distribution_channel_ids=channel_ids,
        article_limit=3,
        draft_limit=3,
    )
    result = await create_admin_task(db, body)
    task_id = result["task"]["id"]

    meta = {
        "source": "monitor_gap",
        "scene_id": scene_id,
        "gap_rate": float(scene_row[3] or 0),
        "gap_priority": gap.get("gap_priority"),
        "legacy_direct_task": True,
    }
    logger.info(
        "gap_task_created_legacy task_id=%s scene_id=%s gap_rate=%s meta=%s",
        task_id,
        scene_id,
        scene_row[3],
        json.dumps(meta, ensure_ascii=False),
    )

    from app.services.geoeval.remediation_service import create_remediation_for_gap

    remediation = await create_remediation_for_gap(
        db,
        scene_id=scene_id,
        task_id=task_id,
        gap_rate=float(scene_row[3] or gap.get("gap_rate") or 0),
        gap_priority=gap.get("gap_priority"),
    )

    if await _table_exists(db, "task_runs"):
        run_id = (
            await db.execute(
                text("SELECT id FROM task_runs WHERE task_id = :tid ORDER BY id DESC LIMIT 1"),
                {"tid": task_id},
            )
        ).scalar_one_or_none()
        if run_id:
            await db.execute(
                text("UPDATE task_runs SET meta = :meta WHERE id = :id"),
                {"meta": json.dumps({**meta, "remediation_id": remediation.get("remediation_id")}), "id": int(run_id)},
            )

    return {
        "mode": "legacy_direct_task",
        "task_id": task_id,
        "task_name": task_name,
        "scene_id": scene_id,
        "gap_rate": float(scene_row[3] or 0),
        "gap_priority": gap.get("gap_priority"),
        "remediation": remediation,
        "deprecated": True,
    }
