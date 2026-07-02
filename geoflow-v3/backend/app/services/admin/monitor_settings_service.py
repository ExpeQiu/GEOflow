"""Monitor 品牌与探针模式设置。"""

import logging

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.production_service import _table_exists
from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting
from app.services.geoeval.monitor_probe import PLATFORMS

logger = logging.getLogger(__name__)


class MonitorSettingsBody(BaseModel):
    brand_name: str = ""
    brand_aliases: str = ""
    probe_mode: str = Field(default="corpus", pattern="^(corpus|llm)$")


async def get_monitor_settings(db: AsyncSession) -> dict:
    settings = get_settings()
    brand_name = settings.app_name
    brand_aliases = ""
    probe_mode = "corpus"

    if await _table_exists(db, "site_settings"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT setting_key, setting_value FROM site_settings
                    WHERE setting_key IN ('brand_name', 'brand_aliases', 'monitor_probe_mode')
                    """
                )
            )
        ).all()
        for key, value in rows:
            if key == "brand_name" and value:
                brand_name = str(value)
            elif key == "brand_aliases":
                brand_aliases = str(value or "")
            elif key == "monitor_probe_mode" and value in ("corpus", "llm"):
                probe_mode = str(value)

    return {
        "brand_name": brand_name,
        "brand_aliases": brand_aliases,
        "probe_mode": probe_mode,
        "platforms": list(PLATFORMS),
        "ai_mock_mode": settings.ai_mock_mode,
    }


async def save_monitor_settings(db: AsyncSession, body: MonitorSettingsBody) -> dict:
    items = [
        ("brand_name", body.brand_name.strip(), "string", "monitor"),
        ("brand_aliases", body.brand_aliases.strip(), "string", "monitor"),
        ("monitor_probe_mode", body.probe_mode, "string", "monitor"),
    ]
    for key, value, vtype, group in items:
        await upsert_site_setting(
            db,
            SiteSettingBody(setting_key=key, setting_value=value, value_type=vtype, group_name=group),
        )
    logger.info("monitor_settings_saved probe_mode=%s", body.probe_mode)
    return await get_monitor_settings(db)
