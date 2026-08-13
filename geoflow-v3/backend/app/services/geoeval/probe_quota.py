"""探针配额：ai_models.daily_limit 护栏，超限写 skipped，禁止静默降级。"""

from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import AiModel
from app.services.geoflow.task_material_resolver import bump_ai_model_usage

logger = logging.getLogger(__name__)


async def resolve_probe_model(db: AsyncSession, *, platform: str, engine_hint: str) -> AiModel | None:
    """优先按平台名匹配 AiModel，否则回落到活跃 chat 模型（LLM/通用配额）。"""
    plat = (platform or "").strip().lower()
    if plat:
        row = (
            await db.execute(
                select(AiModel)
                .where(
                    AiModel.status == "active",
                    or_(
                        AiModel.name.ilike(f"%{plat}%"),
                        AiModel.model_id.ilike(f"%{plat}%"),
                    ),
                )
                .order_by(AiModel.failover_priority, AiModel.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row:
            return row

    if engine_hint in ("llm", "api", "any"):
        row = (
            await db.execute(
                select(AiModel)
                .where(
                    AiModel.status == "active",
                    or_(AiModel.model_type.is_(None), AiModel.model_type == "", AiModel.model_type == "chat"),
                )
                .order_by(AiModel.failover_priority, AiModel.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row
    return None


async def check_probe_quota(
    db: AsyncSession,
    *,
    platform: str,
    engine_hint: str,
) -> tuple[bool, str, int | None]:
    """
    Returns (allowed, skip_reason, model_id).
    daily_limit<=0 视为不限流。
    """
    model = await resolve_probe_model(db, platform=platform, engine_hint=engine_hint)
    if model is None:
        # 无模型配置：允许调用（env Key 直连），但不记账
        return True, "", None

    limit = int(model.daily_limit or 0)
    used = int(model.used_today or 0)
    if limit > 0 and used >= limit:
        logger.warning(
            "probe_quota_exceeded platform=%s model_id=%s used=%s limit=%s",
            platform,
            model.id,
            used,
            limit,
        )
        return False, "daily_limit", int(model.id)
    return True, "", int(model.id)


async def commit_probe_usage(db: AsyncSession, model_id: int | None) -> None:
    if not model_id:
        return
    await bump_ai_model_usage(db, model_id)
    logger.info("probe_usage_bumped model_id=%s", model_id)
