"""真实 AI 平台 API 探针（豆包 / DeepSeek MVP）。"""

import logging
import os

import httpx

from app.services.geoeval.answer_parser import PARSER_VERSION, parse_answer
from app.services.geoeval.platform_connectors.base import ProbeOutcome

logger = logging.getLogger(__name__)


class ApiConnector:
    async def probe(
        self,
        *,
        question_text: str,
        priority: int,
        platform: str,
        corpus: list[dict],
        brand_list: list[str],
        competitor_brands: list[str] | None = None,
    ) -> ProbeOutcome | None:
        try:
            if platform == "deepseek":
                text = await self._call_deepseek(question_text)
            elif platform == "doubao":
                text = await self._call_doubao(question_text)
            else:
                return None
        except Exception as exc:
            logger.warning("api_probe_failed platform=%s error=%s", platform, exc)
            return None

        if not text:
            return None

        parsed = parse_answer(
            text,
            brand_list=brand_list,
            competitor_brands=competitor_brands,
        )
        logger.info(
            "api_probe_parsed platform=%s rank_method=%s evidence_level=%s "
            "parser_version=%s mentioned=%s brand_rank=%s",
            platform,
            parsed.rank_method,
            parsed.evidence_level,
            PARSER_VERSION,
            parsed.mentioned,
            parsed.brand_rank,
        )
        return ProbeOutcome(
            question_id=0,
            platform=platform,
            brand_rank=parsed.brand_rank,
            mentioned=parsed.mentioned,
            snippet=parsed.snippet or text[:240],
            engine="api",
            ranking_score=parsed.ranking_score,
            competitor_mentions=list(parsed.competitor_mentions),
            rank_method=parsed.rank_method,
            evidence_level=parsed.evidence_level,
            match_type=parsed.match_type,
            parser_version=PARSER_VERSION,
            urls=list(parsed.urls),
        )

    async def _call_deepseek(self, question: str) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY missing")
        base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": question}],
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data["choices"][0]["message"]["content"])

    async def _call_doubao(self, question: str) -> str:
        api_key = os.getenv("DOUBAO_API_KEY", "") or os.getenv("ARK_API_KEY", "")
        if not api_key:
            raise ValueError("DOUBAO_API_KEY missing")
        base = os.getenv("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
        model = os.getenv("DOUBAO_MODEL", "")
        if not model:
            raise ValueError("DOUBAO_MODEL missing")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": question}],
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data["choices"][0]["message"]["content"])
