"""探针连接器注册与降级链：api → llm → corpus；strict_api 时禁止静默污染。"""

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


async def load_strict_api(db: AsyncSession) -> bool:
    from sqlalchemy import text

    from app.services.admin.production_service import _table_exists

    if not await _table_exists(db, "site_settings"):
        return False
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_strict_api' LIMIT 1")
        )
    ).scalar_one_or_none()
    return str(row or "").lower() in ("1", "true", "yes", "on")


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


def _skipped_outcome(platform: str, reason: str) -> ProbeOutcome:
    return ProbeOutcome(
        question_id=0,
        platform=platform,
        brand_rank=None,
        mentioned=False,
        snippet=f"[skipped:{reason}]",
        engine="skipped",
        ranking_score=0.0,
        competitor_mentions=[],
    )


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
    strict_api: bool | None = None,
) -> ProbeOutcome:
    outcome: ProbeOutcome | None = None
    if strict_api is None:
        strict_api = await load_strict_api(db)

    if probe_mode == "api":
        outcome = await _api.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )
        if outcome is None and strict_api:
            logger.warning(
                "probe_strict_api_no_fallback platform=%s question_index=%s",
                platform,
                question_index,
            )
            return _skipped_outcome(platform, "api_unavailable_strict")

    if outcome is None and probe_mode in ("api", "llm") and question_index < LLM_MAX_QUESTIONS:
        if not (probe_mode == "api" and strict_api):
            outcome = await LlmConnector(db).probe(
                question_text=question_text,
                priority=priority,
                platform=platform,
                corpus=corpus,
                brand_list=brand_list,
                competitor_brands=competitor_brands,
            )

    if outcome is None:
        if probe_mode == "api" and strict_api:
            return _skipped_outcome(platform, "no_api_result_strict")
        outcome = await _corpus.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )

    # 探针标准：corpus 不得冒充 L1 citation
    if getattr(outcome, "engine", None) == "corpus" and getattr(outcome, "evidence_level", "L0") == "L1":
        try:
            from app.services.admin.geo_eval_settings_service import get_probe_standards

            standards = await get_probe_standards(db)
            if standards.get("forbid_corpus_as_l1", True):
                outcome.evidence_level = "L0"
                logger.info(
                    "probe_corpus_evidence_demoted platform=%s forbid_corpus_as_l1=true",
                    platform,
                )
        except Exception:
            outcome.evidence_level = "L0"

    logger.debug(
        "probe_platform platform=%s engine=%s mentioned=%s rank=%s "
        "rank_method=%s evidence_level=%s parser_version=%s strict=%s",
        platform,
        outcome.engine,
        outcome.mentioned,
        outcome.brand_rank,
        getattr(outcome, "rank_method", "unknown"),
        getattr(outcome, "evidence_level", "L0"),
        getattr(outcome, "parser_version", None),
        strict_api,
    )
    return outcome
