"""真实 AI 平台 API 探针（豆包 / DeepSeek MVP）。"""

import logging
import os
import re

import httpx

from app.services.geoeval.platform_connectors.base import ProbeOutcome, calc_ranking_score

logger = logging.getLogger(__name__)


def _extract_brands(text: str, brands: list[str]) -> tuple[int | None, list[str]]:
    """从回答文本中提取品牌排名。"""
    low = text.lower()
    found: list[tuple[int, str]] = []
    for brand in brands:
        if not brand:
            continue
        match = re.search(re.escape(brand.lower()), low)
        if match:
            found.append((match.start(), brand))
    if not found:
        return None, []
    found.sort(key=lambda x: x[0])
    rank = 1
    target = found[0][1]
    mentions = [b for _, b in found]
    return rank, mentions


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
        all_brands = list(brand_list) + list(competitor_brands or [])
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

        rank, comp_mentions = _extract_brands(text, all_brands)
        self_mentioned = rank is not None and any(b in brand_list for b in (comp_mentions or []))
        if rank is None:
            for idx, brand in enumerate(all_brands, start=1):
                if brand in brand_list and brand.lower() in text.lower():
                    rank = idx
                    self_mentioned = True
                    break

        return ProbeOutcome(
            question_id=0,
            platform=platform,
            brand_rank=rank if self_mentioned else None,
            mentioned=self_mentioned,
            snippet=text[:240],
            engine="api",
            ranking_score=calc_ranking_score(rank if self_mentioned else None),
            competitor_mentions=[c for c in comp_mentions if c not in brand_list],
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
