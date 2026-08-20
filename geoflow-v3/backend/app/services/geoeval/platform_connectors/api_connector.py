"""真实 AI 平台 API 探针（豆包 / DeepSeek / Kimi）。"""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlparse

import httpx

from app.services.geoeval.answer_parser import PARSER_VERSION, parse_answer
from app.services.geoeval.platform_connectors.base import ProbeOutcome
from app.services.geoeval.probe_scheme import (
    SCHEME_CITATION,
    SCHEME_FRAMEWORK_API,
    SCHEME_OPEN_API,
    stamp_outcome,
)

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.S | re.I)

MOCK_COT = (
    "首先澄清使用场景是市内代步还是长途再谈电池化学。"
    "对比维度：安全、低温续航、循环寿命、成本、补能效率。"
    "证据门槛：需要冬测达成率和第三方循环寿命，不能只看标称能量密度。"
    "场景约束：北方冬天、家用只有慢充桩。"
    "未决缺口：没有第三方维修价和保费数据，不敢下结论。"
    "用户可能还会问 CTC 撞了保费会不会涨。"
)

MOCK_ANSWER = (
    "磷酸铁锂更适合日常代步与安全敏感用户，三元锂更适合低温长途；"
    "最终应以冬测达成率和循环寿命实测为准，而不是只看能量密度。"
)

MOCK_CITATION_ANSWER = (
    "1. 吉利银河适合家用智能驾驶新能源。"
    "官方说明见 https://127.0.0.1:3070/concepts/lfp-vs-ncm 。"
    "第三方评测 https://www.autohome.com.cn/drive/2026/lfp 。"
    "百科背景 https://zh.wikipedia.org/wiki/磷酸铁锂电池 。"
)

_CITE_HINT = (
    "\n\n请在回答中给出可核验的资料链接（官方站点、百科或媒体），使用完整 https URL。"
)


def _citation_web_search_enabled() -> bool:
    return os.getenv("CITATION_WEB_SEARCH", "").lower() in ("1", "true", "yes", "on")


def _mock_enabled() -> bool:
    return os.getenv("AI_MOCK_MODE", "").lower() in ("1", "true", "yes", "on")


def split_reasoning(message: dict | None, content: str) -> tuple[str, str]:
    """分离最终回答与明文思维链。"""
    msg = message or {}
    reasoning = str(msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
    text = str(content or msg.get("content") or "").strip()
    if not reasoning:
        m = _THINK_RE.search(text)
        if m:
            reasoning = m.group(1).strip()
            text = (_THINK_RE.sub("", text)).strip()
    return text, reasoning


def _hosts_of(urls: list[str]) -> list[str]:
    out: list[str] = []
    for u in urls:
        host = (urlparse(u).hostname or "").lower()
        if host and host not in out:
            out.append(host)
    return out


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
        scheme: str = SCHEME_OPEN_API,
        official_domains: list[str] | None = None,
        wiki_domains: list[str] | None = None,
    ) -> ProbeOutcome | None:
        enable_thinking = scheme == SCHEME_FRAMEWORK_API
        enable_citation = scheme == SCHEME_CITATION
        prompt = question_text + (_CITE_HINT if enable_citation else "")
        citation_method = "url_extract"
        try:
            if _mock_enabled() and enable_thinking:
                text, reasoning = MOCK_ANSWER, MOCK_COT
            elif _mock_enabled() and enable_citation:
                text, reasoning = MOCK_CITATION_ANSWER, ""
                citation_method = "mock"
            elif platform == "deepseek":
                text, reasoning = await self._call_deepseek(prompt, enable_thinking=enable_thinking)
            elif platform == "doubao":
                text, reasoning = await self._call_doubao(prompt, enable_thinking=enable_thinking)
            elif platform == "kimi" and enable_citation:
                use_search = _citation_web_search_enabled()
                text, reasoning = await self._call_kimi(prompt, web_search=use_search)
                citation_method = "web_search" if use_search else "url_extract"
            else:
                return None
        except Exception as exc:
            logger.warning(
                "api_probe_failed platform=%s scheme=%s error=%s",
                platform,
                scheme,
                exc,
            )
            if enable_thinking and _mock_enabled():
                text, reasoning = MOCK_ANSWER, MOCK_COT
            elif enable_citation and _mock_enabled():
                text, reasoning = MOCK_CITATION_ANSWER, ""
                citation_method = "mock"
            else:
                return None

        if not text and not reasoning:
            return None

        parsed = parse_answer(
            text or (MOCK_CITATION_ANSWER if enable_citation else MOCK_ANSWER),
            brand_list=brand_list,
            competitor_brands=competitor_brands,
            official_domains=official_domains,
            wiki_domains=wiki_domains,
        )
        logger.info(
            "api_probe_parsed platform=%s scheme=%s rank_method=%s evidence_level=%s "
            "parser_version=%s mentioned=%s brand_rank=%s has_reasoning=%s urls=%s match_type=%s citation_method=%s",
            platform,
            scheme,
            parsed.rank_method,
            parsed.evidence_level,
            PARSER_VERSION,
            parsed.mentioned,
            parsed.brand_rank,
            bool(reasoning),
            len(parsed.urls),
            parsed.match_type,
            citation_method,
        )
        outcome = ProbeOutcome(
            question_id=0,
            platform=platform,
            brand_rank=parsed.brand_rank,
            mentioned=parsed.mentioned,
            snippet=parsed.snippet or (text or "")[:240],
            engine="api",
            ranking_score=parsed.ranking_score,
            competitor_mentions=list(parsed.competitor_mentions),
            rank_method=parsed.rank_method,
            evidence_level=parsed.evidence_level,
            match_type=parsed.match_type,
            parser_version=PARSER_VERSION,
            urls=list(parsed.urls),
            citation_urls=list(parsed.urls),
            source_hosts=_hosts_of(parsed.urls),
            thinking_text=(reasoning[:8000] if reasoning else None),
            citation_method=citation_method,
        )
        return stamp_outcome(outcome, scheme=scheme)

    async def _call_deepseek(self, question: str, *, enable_thinking: bool) -> tuple[str, str]:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            if enable_thinking and _mock_enabled():
                return MOCK_ANSWER, MOCK_COT
            raise ValueError("DEEPSEEK_API_KEY missing")
        base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        if enable_thinking:
            model = os.getenv("DEEPSEEK_THINKING_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            max_tokens = int(os.getenv("DEEPSEEK_THINKING_MAX_TOKENS", "4000"))
            timeout = 90.0
        else:
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            max_tokens = 800
            timeout = 30.0
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": max_tokens,
        }
        if enable_thinking:
            payload["thinking"] = {"type": "enabled"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = ((data.get("choices") or [{}])[0].get("message")) or {}
            return split_reasoning(msg, str(msg.get("content") or ""))

    async def _call_doubao(self, question: str, *, enable_thinking: bool) -> tuple[str, str]:
        api_key = os.getenv("DOUBAO_API_KEY", "") or os.getenv("ARK_API_KEY", "")
        if not api_key:
            if enable_thinking and _mock_enabled():
                return MOCK_ANSWER, MOCK_COT
            raise ValueError("DOUBAO_API_KEY missing")
        base = os.getenv("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
        model = os.getenv("DOUBAO_MODEL", "")
        if not model:
            raise ValueError("DOUBAO_MODEL missing")
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 4000 if enable_thinking else 800,
        }
        if enable_thinking:
            payload["thinking"] = {"type": "enabled"}
        timeout = 90.0 if enable_thinking else 30.0
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = ((data.get("choices") or [{}])[0].get("message")) or {}
            return split_reasoning(msg, str(msg.get("content") or ""))

    async def _call_kimi(self, question: str, *, web_search: bool = False) -> tuple[str, str]:
        api_key = os.getenv("KIMI_API_KEY", "") or os.getenv("MOONSHOT_API_KEY", "")
        if not api_key:
            if _mock_enabled():
                return MOCK_CITATION_ANSWER, ""
            raise ValueError("KIMI_API_KEY missing")
        base = os.getenv("KIMI_API_BASE", "https://api.moonshot.cn/v1")
        model = os.getenv("KIMI_MODEL", "moonshot-v1-auto")
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 1200,
        }
        if web_search:
            payload["tools"] = [{"type": "builtin_function", "function": {"name": "$web_search"}}]
        try:
            async with httpx.AsyncClient(timeout=60.0 if web_search else 45.0) as client:
                resp = await client.post(
                    f"{base.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                msg = ((data.get("choices") or [{}])[0].get("message")) or {}
                return split_reasoning(msg, str(msg.get("content") or ""))
        except Exception:
            if web_search:
                logger.warning("kimi_web_search_fallback_url_extract", exc_info=True)
                return await self._call_kimi(question, web_search=False)
            raise
