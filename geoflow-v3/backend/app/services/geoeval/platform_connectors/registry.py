"""探针连接器注册与降级链：api → llm → corpus。"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geoeval.platform_connectors.api_connector import ApiConnector
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN, ProbeOutcome
from app.services.geoeval.platform_connectors.corpus_connector import CorpusConnector
from app.services.geoeval.platform_connectors.llm_connector import LlmConnector

logger = logging.getLogger(__name__)

_corpus = CorpusConnector()
_api = ApiConnector()
LLM_MAX_QUESTIONS = 5


async def load_probe_mode(db: AsyncSession) -> str:
    from sqlalchemy import text

    from app.services.admin.production_service import _table_exists

    if not await _table_exists(db, "site_settings"):
        return "corpus"
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_probe_mode' LIMIT 1")
        )
    ).scalar_one_or_none()
    mode = str(row) if row else "corpus"
    return mode if mode in ("corpus", "llm", "api") else "corpus"


async def load_platforms(db: AsyncSession) -> tuple[str, ...]:
    from sqlalchemy import text

    from app.services.admin.production_service import _table_exists

    if not await _table_exists(db, "site_settings"):
        return PLATFORMS_CN
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_platforms' LIMIT 1")
        )
    ).scalar_one_or_none()
    if not row:
        return PLATFORMS_CN
    platforms = tuple(p.strip() for p in str(row).split(",") if p.strip())
    return platforms or PLATFORMS_CN


async def probe_platform(
    db: AsyncSession,
    *,
    question_text: str,
    priority: int,
    platform: str,
    corpus: list[dict],
    brand_list: list[str],
    competitor_brands: list[str] | None,
    probe_mode: str,
    question_index: int,
) -> ProbeOutcome:
    outcome: ProbeOutcome | None = None

    if probe_mode == "api":
        outcome = await _api.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )

    if outcome is None and probe_mode in ("api", "llm") and question_index < LLM_MAX_QUESTIONS:
        outcome = await LlmConnector(db).probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )

    if outcome is None:
        outcome = await _corpus.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )

    logger.debug(
        "probe_platform platform=%s engine=%s mentioned=%s rank=%s",
        platform,
        outcome.engine,
        outcome.mentioned,
        outcome.brand_rank,
    )
    return outcome
