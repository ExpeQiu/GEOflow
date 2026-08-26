"""CendBrowserConnector：把捕获结果转为 ProbeOutcome。"""

from __future__ import annotations

import logging
import os

from app.services.geoeval.answer_parser import PARSER_VERSION, parse_answer
from app.services.geoeval.platform_connectors.base import ProbeOutcome, calc_ranking_score
from app.services.geoeval.platform_connectors.cend.browser_session import (
    check_profile_ready,
    close_context,
    launch_persistent_context,
)
from app.services.geoeval.platform_connectors.cend.registry import get_cend_adapter

logger = logging.getLogger(__name__)


def _mock_enabled() -> bool:
    return os.getenv("CEND_MOCK_MODE", "").lower() in ("1", "true", "yes") or os.getenv(
        "AI_MOCK_MODE", ""
    ).lower() in ("1", "true", "yes")


class CendBrowserConnector:
    async def probe(
        self,
        *,
        question_text: str,
        platform: str,
        brand_list: list[str],
        competitor_brands: list[str] | None = None,
        question_id: int = 0,
    ) -> ProbeOutcome:
        brands = list(brand_list or [])
        comps = list(competitor_brands or [])

        if _mock_enabled():
            return self._mock_outcome(question_text, platform, brands, comps, question_id)

        adapter = get_cend_adapter(platform)
        try:
            context = await launch_persistent_context(platform)
        except RuntimeError as exc:
            logger.warning("cend_probe_skipped platform=%s reason=%s", platform, exc)
            return self._skip_outcome(platform, question_id, reason=str(exc))

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            captured = await adapter.capture(page, question_text, brand_list=brands)
        finally:
            await close_context(context)

        if not captured.ok:
            return self._skip_outcome(
                platform,
                question_id,
                reason=captured.error or "capture_failed",
                cend_meta=captured.meta,
                capture_artifact=captured.capture_artifact,
            )

        parsed = parse_answer(
            captured.answer_text,
            brand_list=brands,
            competitor_brands=comps,
        )
        # 若阵营块给出更清晰排名，优先 camp
        rank_method = parsed.rank_method
        brand_rank = parsed.brand_rank
        if captured.rank_blocks:
            camp_ranks = [b.get("brand_rank") for b in captured.rank_blocks if b.get("brand_rank") is not None]
            if camp_ranks:
                brand_rank = min(int(r) for r in camp_ranks)
                rank_method = "camp_block"

        cite_urls = [c.get("url", "") for c in captured.citations if c.get("url")]
        cite_titles = [c.get("title", "") for c in captured.citations]
        mentioned = parsed.mentioned or any(b in captured.answer_text for b in brands)

        outcome = ProbeOutcome(
            question_id=question_id,
            platform=platform,
            brand_rank=brand_rank if mentioned else None,
            mentioned=mentioned,
            snippet=(captured.answer_text or "")[:240],
            engine="cend_browser",
            ranking_score=calc_ranking_score(brand_rank if mentioned else None),
            competitor_mentions=list(parsed.competitor_mentions),
            rank_method=rank_method,
            evidence_level="L2" if cite_urls else "L0",
            match_type=parsed.match_type,
            parser_version=PARSER_VERSION,
            urls=cite_urls or list(parsed.urls),
            thinking_text=captured.thinking_text or None,
            thinking_ms=captured.thinking_ms,
            keywords=captured.keywords,
            entities=captured.entities,
            rank_blocks=captured.rank_blocks,
            decision_table=captured.decision_table,
            citation_urls=cite_urls,
            citation_titles=cite_titles,
            source_hosts=captured.source_hosts,
            capture_artifact=captured.capture_artifact,
            metric_kind="cend_sample",
            cend_meta={**captured.meta, "citation_count": len(cite_urls)},
        )
        from app.services.geoeval.probe_scheme import SCHEME_CEND, stamp_outcome

        return stamp_outcome(outcome, scheme=SCHEME_CEND)

    def _skip_outcome(
        self,
        platform: str,
        question_id: int,
        *,
        reason: str,
        cend_meta: dict | None = None,
        capture_artifact: str | None = None,
    ) -> ProbeOutcome:
        from app.services.geoeval.probe_scheme import SCHEME_CEND, stamp_outcome

        outcome = ProbeOutcome(
            question_id=question_id,
            platform=platform,
            brand_rank=None,
            mentioned=False,
            snippet=f"[skipped:{reason}]",
            engine="skipped",
            metric_kind="cend_sample",
            evidence_level="L0",
            capture_artifact=capture_artifact,
            cend_meta={**(cend_meta or {}), "skip_reason": reason},
        )
        return stamp_outcome(outcome, scheme=SCHEME_CEND)

    def _mock_outcome(
        self,
        question_text: str,
        platform: str,
        brands: list[str],
        comps: list[str],
        question_id: int,
    ) -> ProbeOutcome:
        brand = brands[0] if brands else "品牌"
        answer = (
            f"### 城区NOA第一梯队：竞品阵营\n"
            f"1. 小鹏 G6\n2. {brand} 银河\n3. 问界 M5\n\n"
            f"| 诉求 | 首选 | 备选 |\n| --- | --- | --- |\n| 城区NOA | 小鹏 | {brand} |\n\n"
            f"参考 https://www.autohome.com.cn/mock/{platform} 与 https://auto.sina.com.cn/mock\n"
            f"问题：{question_text[:80]}"
        )
        parsed = parse_answer(answer, brand_list=brands, competitor_brands=comps)
        urls = [
            f"https://www.autohome.com.cn/mock/{platform}",
            "https://auto.sina.com.cn/mock",
        ]
        outcome = ProbeOutcome(
            question_id=question_id,
            platform=platform,
            brand_rank=parsed.brand_rank,
            mentioned=parsed.mentioned,
            snippet=answer[:240],
            engine="cend_browser",
            ranking_score=calc_ranking_score(parsed.brand_rank),
            competitor_mentions=list(parsed.competitor_mentions),
            rank_method=parsed.rank_method,
            evidence_level="L2",
            match_type="none",
            parser_version=PARSER_VERSION,
            urls=urls,
            thinking_text="已深度思考（Mock）：核对价位与城区NOA能力。",
            thinking_ms=12000,
            keywords=["城区NOA", "智驾", brand],
            entities=brands[:6],
            rank_blocks=[
                {
                    "camp": "城区NOA第一梯队：竞品阵营",
                    "brand_rank": parsed.brand_rank,
                    "mentioned": parsed.mentioned,
                    "models": [
                        {"position": 1, "text": "小鹏 G6"},
                        {"position": 2, "text": f"{brand} 银河"},
                    ],
                }
            ],
            decision_table=[{"诉求": "城区NOA", "首选": "小鹏", "备选": brand}],
            citation_urls=urls,
            citation_titles=["汽车之家参考", "新浪汽车参考"],
            source_hosts=["autohome.com.cn", "auto.sina.com.cn"],
            capture_artifact=None,
            metric_kind="cend_sample",
            cend_meta={"mock": True, "platform": platform},
        )
        from app.services.geoeval.probe_scheme import SCHEME_CEND, stamp_outcome

        return stamp_outcome(outcome, scheme=SCHEME_CEND)


async def probe_cend_platform(
    *,
    question_text: str,
    platform: str,
    brand_list: list[str],
    competitor_brands: list[str] | None = None,
    question_id: int = 0,
) -> ProbeOutcome:
    return await CendBrowserConnector().probe(
        question_text=question_text,
        platform=platform,
        brand_list=brand_list,
        competitor_brands=competitor_brands,
        question_id=question_id,
    )


__all__ = ["CendBrowserConnector", "probe_cend_platform", "check_profile_ready"]
