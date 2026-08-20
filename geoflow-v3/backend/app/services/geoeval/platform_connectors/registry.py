"""探针连接器注册与降级链：api → llm → corpus；strict_api 时禁止静默污染。"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geoeval.platform_connectors.api_connector import ApiConnector
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN, ProbeOutcome
from app.services.geoeval.platform_connectors.corpus_connector import CorpusConnector
from app.services.geoeval.platform_connectors.llm_connector import LlmConnector
from app.services.geoeval.probe_scheme import SCHEME_DEV, SCHEME_OPEN_API, stamp_outcome

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

    if await _table_exists(db, "site_settings"):
        row = (
            await db.execute(
                text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_platforms' LIMIT 1")
            )
        ).scalar_one_or_none()
        if row and str(row).strip():
            platforms = tuple(p.strip() for p in str(row).split(",") if p.strip())
            if platforms:
                return platforms

        # 未配置 monitor_platforms 时，用探针标准 scan_platforms（默认豆包+DeepSeek）
        row2 = (
            await db.execute(
                text("SELECT setting_value FROM site_settings WHERE setting_key = 'probe_scan_platforms' LIMIT 1")
            )
        ).scalar_one_or_none()
        if row2 and str(row2).strip():
            plats = tuple(p.strip() for p in str(row2).split(",") if p.strip())
            if plats:
                return plats

    try:
        from app.services.admin.geo_eval_settings_service import get_probe_standards

        standards = await get_probe_standards(db)
        raw = str(standards.get("scan_platforms") or "").strip()
        if raw:
            plats = tuple(p.strip() for p in raw.split(",") if p.strip())
            if plats:
                return plats
    except Exception:
        pass

    return PLATFORMS_CN


def _skipped_outcome(platform: str, reason: str) -> ProbeOutcome:
    o = ProbeOutcome(
        question_id=0,
        platform=platform,
        brand_rank=None,
        mentioned=False,
        snippet=f"[skipped:{reason}]",
        engine="skipped",
        ranking_score=0.0,
        competitor_mentions=[],
        tracks=[],
        reasoning_grade="none",
        metric_kind="mixed",
    )
    return stamp_outcome(o, scheme=SCHEME_OPEN_API)


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
    scheme: str = SCHEME_OPEN_API,
) -> ProbeOutcome:
    outcome: ProbeOutcome | None = None
    if strict_api is None:
        strict_api = await load_strict_api(db)

    from app.services.geoeval.probe_quota import check_probe_quota, commit_probe_usage

    # M1：走 api/llm 前检查 daily_limit；超限直接 skipped，禁止 corpus 填洞
    needs_quota = probe_mode in ("api", "llm")
    model_id: int | None = None
    if needs_quota:
        allowed, skip_reason, model_id = await check_probe_quota(
            db, platform=platform, engine_hint="api" if probe_mode == "api" else "llm"
        )
        if not allowed:
            logger.warning(
                "probe_skipped_daily_limit platform=%s mode=%s reason=%s",
                platform,
                probe_mode,
                skip_reason,
            )
            return _skipped_outcome(platform, skip_reason or "daily_limit")

    if probe_mode == "api":
        outcome = await _api.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
            scheme=scheme,
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
        # 超限后禁止 corpus；strict 同理。普通 corpus 模式仍可用。
        if needs_quota and model_id is not None:
            # 已过配额检查但 api/llm 失败：strict 已返回；非 strict 可 corpus，不计配额
            pass
        outcome = await _corpus.probe(
            question_text=question_text,
            priority=priority,
            platform=platform,
            corpus=corpus,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )

    # 成功 api/llm 才 bump 用量
    if outcome is not None and getattr(outcome, "engine", None) in ("api", "llm"):
        await commit_probe_usage(db, model_id)

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

    if outcome is not None:
        eng = getattr(outcome, "engine", None)
        if eng == "api":
            stamp_outcome(outcome, scheme=scheme or SCHEME_OPEN_API)
        elif eng in ("corpus", "llm"):
            stamp_outcome(outcome, scheme=SCHEME_DEV)

    logger.debug(
        "probe_platform platform=%s engine=%s mentioned=%s rank=%s "
        "rank_method=%s evidence_level=%s parser_version=%s strict=%s scheme=%s tracks=%s",
        platform,
        outcome.engine,
        outcome.mentioned,
        outcome.brand_rank,
        getattr(outcome, "rank_method", "unknown"),
        getattr(outcome, "evidence_level", "L0"),
        getattr(outcome, "parser_version", None),
        strict_api,
        getattr(outcome, "scheme", None),
        getattr(outcome, "tracks", None),
    )
    return outcome
