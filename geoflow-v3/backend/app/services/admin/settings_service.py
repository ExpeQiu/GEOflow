"""站点设置只读 API。"""

from app.core.config import get_settings


def build_site_settings_payload() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "geo_eval_enabled": settings.geo_eval_enabled,
        "geo_eval_wiki_gate_enabled": settings.geo_eval_wiki_gate_enabled,
        "tech_brand_mode": settings.geoflow_tech_brand_mode,
        "public_site_enabled": settings.geoflow_public_site_enabled,
        "ai_mock_mode": settings.ai_mock_mode,
        "gweb_sync_enabled": settings.gweb_sync_enabled,
    }
