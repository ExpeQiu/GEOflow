"""站点设置只读 API + 安全运行态（不返回密钥明文）。"""

from app.core.config import _INSECURE_JWT_SECRETS, get_settings
from app.core.security import ADMIN_COOKIE_NAME


def _jwt_secret_strong(secret: str) -> bool:
    s = (secret or "").strip()
    return s not in _INSECURE_JWT_SECRETS and len(s) >= 24


def build_security_runtime_payload() -> dict:
    """给 Admin 设置页展示的安全/集成运行态（无密钥）。"""
    settings = get_settings()
    cb = (settings.content_agent_callback_secret or "").strip()
    callback_ok = cb not in ("", "dev-callback-secret")
    jwt_ok = _jwt_secret_strong(settings.jwt_secret)
    lobster_ok = bool((settings.lobster_proxy_token or "").strip())
    enterprise_ok = bool((settings.enterprise_ai_gateway_api_key or "").strip())
    return {
        "debug": settings.debug,
        "allow_insecure_jwt": settings.allow_insecure_jwt,
        "jwt_secret_strong": jwt_ok,
        "jwt_expire_hours": settings.jwt_expire_hours,
        "api_token_default_ttl_days": settings.api_token_default_ttl_days,
        "cors_allowed_origins": settings.cors_origins_list(),
        "callback_secret_configured": callback_ok,
        "login_max_failures": settings.login_max_failures,
        "login_lockout_seconds": settings.login_lockout_seconds,
        "http_only_cookie": True,
        "admin_cookie_name": ADMIN_COOKIE_NAME,
        "uploads_auth_required": True,
        "ws_auth_required": True,
        "llm_gateway_mode": settings.llm_gateway_mode,
        "enterprise_text_base": settings.enterprise_ai_text_base_url.rstrip("/"),
        "enterprise_key_configured": enterprise_ok,
        "lobster_proxy_base": settings.lobster_proxy_base.rstrip("/"),
        "lobster_token_configured": lobster_ok,
        "api_key_encryption_separate": bool((settings.api_key_encryption_key or "").strip()),
        "production_ready": (
            not settings.debug
            and not settings.allow_insecure_jwt
            and jwt_ok
            and callback_ok
        ),
        "env_hints": {
            "jwt_secret": "JWT_SECRET",
            "callback_secret": "CONTENT_AGENT_CALLBACK_SECRET",
            "cors": "CORS_ALLOWED_ORIGINS",
            "allow_insecure": "ALLOW_INSECURE_JWT",
            "lobster_token": "LOBSTER_PROXY_TOKEN",
            "enterprise_key": "ENTERPRISE_AI_GATEWAY_API_KEY",
            "llm_gateway": "LLM_GATEWAY_MODE",
        },
    }


def build_site_settings_payload() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "geo_eval_enabled": settings.geo_eval_enabled,
        "geo_eval_wiki_gate_enabled": settings.geo_eval_wiki_gate_enabled,
        "geo_eval_hard_gate": settings.geo_eval_hard_gate,
        "tech_brand_mode": settings.geoflow_tech_brand_mode,
        "public_site_enabled": settings.geoflow_public_site_enabled,
        "ai_mock_mode": settings.ai_mock_mode,
        "geoweb_sync_enabled": settings.geoweb_sync_enabled,
        "geoweb_base_url": settings.geoweb_base_url,
        "llm_gateway_mode": settings.llm_gateway_mode,
        "enterprise_text_base": settings.enterprise_ai_text_base_url.rstrip("/"),
        "enterprise_key_configured": bool((settings.enterprise_ai_gateway_api_key or "").strip()),
        "lobster_proxy_base": settings.lobster_proxy_base.rstrip("/"),
        "lobster_token_configured": bool((settings.lobster_proxy_token or "").strip()),
        "security_runtime": build_security_runtime_payload(),
    }
