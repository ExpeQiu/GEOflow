"""Monitor 品牌与探针模式设置。"""

import logging

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.production_service import _table_exists
from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN
from app.services.geoeval.domain_catalog import DEFAULT_OFFICIAL_DOMAINS

logger = logging.getLogger(__name__)


class MonitorSettingsBody(BaseModel):
    brand_name: str = ""
    brand_aliases: str = ""
    probe_mode: str = Field(default="corpus", pattern="^(corpus|llm|api)$")
    monitor_platforms: str = ""
    monitor_scan_limit: int = Field(default=50, ge=1, le=500)
    default_knowledge_base_id: int | None = None
    strict_api: bool = False
    remediation_delay_hours: int = Field(default=72, ge=0, le=720)
    gap_rag_score_threshold: float = Field(default=0.3, ge=0.05, le=0.95)
    official_domains: str = ""
    competitor_domains: str = ""
    wiki_domains: str = ""


def _as_bool(value: str | None) -> bool:
    return str(value or "").lower() in ("1", "true", "yes", "on")


async def get_monitor_settings(db: AsyncSession) -> dict:
    settings = get_settings()
    brand_name = settings.app_name
    brand_aliases = ""
    probe_mode = "corpus"
    monitor_platforms = ",".join(PLATFORMS_CN)
    monitor_scan_limit = 50
    default_knowledge_base_id: int | None = None
    strict_api = False
    remediation_delay_hours = 72
    gap_rag_score_threshold = 0.3
    official_domains = ""
    competitor_domains = ""
    wiki_domains = ""

    if await _table_exists(db, "site_settings"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT setting_key, setting_value FROM site_settings
                    WHERE setting_key IN (
                        'brand_name', 'brand_aliases', 'monitor_probe_mode',
                        'monitor_platforms', 'monitor_scan_limit', 'default_knowledge_base_id',
                        'monitor_strict_api', 'remediation_delay_hours', 'gap_rag_score_threshold',
                        'official_domains', 'competitor_domains', 'wiki_domains'
                    )
                    """
                )
            )
        ).all()
        for key, value in rows:
            if key == "brand_name" and value:
                brand_name = str(value)
            elif key == "brand_aliases":
                brand_aliases = str(value or "")
            elif key == "monitor_probe_mode" and value in ("corpus", "llm", "api"):
                probe_mode = str(value)
            elif key == "monitor_platforms" and value:
                monitor_platforms = str(value)
            elif key == "monitor_scan_limit" and value:
                try:
                    monitor_scan_limit = int(value)
                except (TypeError, ValueError):
                    pass
            elif key == "default_knowledge_base_id" and value:
                try:
                    default_knowledge_base_id = int(value)
                except (TypeError, ValueError):
                    pass
            elif key == "monitor_strict_api":
                strict_api = _as_bool(str(value))
            elif key == "remediation_delay_hours" and value is not None:
                try:
                    remediation_delay_hours = max(0, min(720, int(value)))
                except (TypeError, ValueError):
                    pass
            elif key == "gap_rag_score_threshold" and value is not None:
                try:
                    gap_rag_score_threshold = max(0.05, min(0.95, float(value)))
                except (TypeError, ValueError):
                    pass
            elif key == "official_domains":
                official_domains = str(value or "")
            elif key == "competitor_domains":
                competitor_domains = str(value or "")
            elif key == "wiki_domains":
                wiki_domains = str(value or "")

    platforms = tuple(p.strip() for p in monitor_platforms.split(",") if p.strip()) or PLATFORMS_CN
    if not official_domains.strip():
        official_domains = ",".join(DEFAULT_OFFICIAL_DOMAINS)

    return {
        "brand_name": brand_name,
        "brand_aliases": brand_aliases,
        "probe_mode": probe_mode,
        "monitor_platforms": monitor_platforms,
        "monitor_scan_limit": monitor_scan_limit,
        "default_knowledge_base_id": default_knowledge_base_id,
        "platforms": list(platforms),
        "ai_mock_mode": settings.ai_mock_mode,
        "strict_api": strict_api,
        "remediation_delay_hours": remediation_delay_hours,
        "gap_rag_score_threshold": gap_rag_score_threshold,
        "official_domains": official_domains,
        "competitor_domains": competitor_domains,
        "wiki_domains": wiki_domains,
        "geoweb_base_url": settings.geoweb_base_url,
    }


async def save_monitor_settings(db: AsyncSession, body: MonitorSettingsBody) -> dict:
    items = [
        ("brand_name", body.brand_name.strip(), "string", "monitor"),
        ("brand_aliases", body.brand_aliases.strip(), "string", "monitor"),
        ("monitor_probe_mode", body.probe_mode, "string", "monitor"),
        ("monitor_platforms", body.monitor_platforms.strip() or ",".join(PLATFORMS_CN), "string", "monitor"),
        ("monitor_scan_limit", str(body.monitor_scan_limit), "integer", "monitor"),
        (
            "default_knowledge_base_id",
            str(body.default_knowledge_base_id or ""),
            "integer",
            "monitor",
        ),
        ("monitor_strict_api", "true" if body.strict_api else "false", "boolean", "monitor"),
        ("remediation_delay_hours", str(body.remediation_delay_hours), "integer", "monitor"),
        ("gap_rag_score_threshold", str(body.gap_rag_score_threshold), "float", "monitor"),
        ("official_domains", body.official_domains.strip(), "string", "monitor"),
        ("competitor_domains", body.competitor_domains.strip(), "string", "monitor"),
        ("wiki_domains", body.wiki_domains.strip(), "string", "monitor"),
    ]
    for key, value, vtype, group in items:
        await upsert_site_setting(
            db,
            SiteSettingBody(setting_key=key, setting_value=value, value_type=vtype, group_name=group),
        )
    logger.info(
        "monitor_settings_saved probe_mode=%s platforms=%s strict_api=%s delay_h=%s",
        body.probe_mode,
        body.monitor_platforms,
        body.strict_api,
        body.remediation_delay_hours,
    )
    return await get_monitor_settings(db)
