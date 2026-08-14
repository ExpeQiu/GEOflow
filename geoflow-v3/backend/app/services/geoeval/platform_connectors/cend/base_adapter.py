"""通用 C 端适配器基类：发问 + 等待 + 抽取 + 启发式结构化。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.services.geoeval.platform_connectors.cend.browser_session import cend_artifact_dir
from app.services.geoeval.platform_connectors.cend.parse_helpers import (
    citations_from_pairs,
    domain_of,
    extract_decision_table_heuristic,
    extract_keywords,
    extract_rank_blocks,
)
from app.services.geoeval.platform_connectors.cend.protocol import CendCaptureResult

logger = logging.getLogger(__name__)


class BaseCendAdapter:
    platform: str = ""
    start_url: str = ""
    # 输入框 / 发送 / 资料列表 / 思考区 — 子类覆盖
    input_selectors: tuple[str, ...] = (
        "textarea",
        "[contenteditable='true']",
        "div[role='textbox']",
    )
    send_selectors: tuple[str, ...] = (
        "button[type='submit']",
        "button:has-text('发送')",
        "button:has-text('提交')",
    )
    answer_selectors: tuple[str, ...] = (
        "[class*='markdown']",
        "[class*='answer']",
        "[class*='message']",
        "article",
    )
    thinking_selectors: tuple[str, ...] = (
        "text=已深度思考",
        "text=深度思考",
        "[class*='think']",
        "[class*='reasoning']",
    )
    citation_link_selectors: tuple[str, ...] = (
        "a[href^='http']",
    )
    materials_header_re = re.compile(r"找到了\s*(\d+)\s*篇|相关资料|引用\s*\d+|参考资料")

    async def _first_visible(self, page: Any, selectors: tuple[str, ...]):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    async def _type_question(self, page: Any, question_text: str) -> bool:
        box = await self._first_visible(page, self.input_selectors)
        if box is None:
            return False
        await box.click()
        await box.fill("")
        await box.type(question_text, delay=15)
        send = await self._first_visible(page, self.send_selectors)
        if send is not None:
            await send.click()
        else:
            await page.keyboard.press("Enter")
        return True

    async def _wait_answer(self, page: Any, timeout_ms: int = 90000) -> None:
        await page.wait_for_timeout(2500)
        # 等网络大致安静；失败不抛
        try:
            await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 30000))
        except Exception:
            pass
        await page.wait_for_timeout(3000)

    async def _extract_answer_text(self, page: Any) -> str:
        for sel in self.answer_selectors:
            try:
                locs = page.locator(sel)
                n = await locs.count()
                if n <= 0:
                    continue
                # 取最后一个可见大块
                for i in range(n - 1, -1, -1):
                    el = locs.nth(i)
                    if not await el.is_visible():
                        continue
                    text = (await el.inner_text()).strip()
                    if len(text) > 80:
                        return text
            except Exception:
                continue
        try:
            return (await page.inner_text("body"))[:12000]
        except Exception:
            return ""

    async def _extract_thinking(self, page: Any) -> tuple[str, int | None]:
        thinking = ""
        ms = None
        for sel in self.thinking_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() == 0:
                    continue
                # 尝试展开
                try:
                    await loc.click(timeout=2000)
                    await page.wait_for_timeout(500)
                except Exception:
                    pass
                parent = loc.locator("xpath=ancestor::*[1]")
                thinking = (await parent.inner_text()).strip()[:6000]
                m = re.search(r"用时\s*(\d+)\s*秒", thinking)
                if m:
                    ms = int(m.group(1)) * 1000
                if thinking:
                    break
            except Exception:
                continue
        return thinking, ms

    async def _extract_citations(self, page: Any) -> list[dict]:
        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        # 优先「相关资料」区域附近的链接
        try:
            body = await page.inner_text("body")
        except Exception:
            body = ""
        # 全页 http 链接
        try:
            anchors = page.locator("a[href^='http']")
            n = min(await anchors.count(), 80)
            for i in range(n):
                a = anchors.nth(i)
                href = (await a.get_attribute("href")) or ""
                title = ((await a.inner_text()) or "").strip() or href
                if not href or href in seen:
                    continue
                host = (urlparse(href).hostname or "").lower()
                # 过滤平台自身域名噪音
                if any(x in host for x in ("tencent.com", "yuanbao", "doubao.com", "moonshot", "aliyun", "baidu.com", "deepseek")):
                    if "autohome" not in href and "sina" not in href:
                        # 仍允许外链；平台域名跳过
                        if host.endswith(("tencent.com", "doubao.com", "aliyun.com", "baidu.com", "moonshot.cn", "deepseek.com")):
                            continue
                seen.add(href)
                pairs.append((title[:200], href))
        except Exception:
            logger.debug("cend_citation_extract_failed platform=%s", self.platform, exc_info=True)

        # 若正文提到「找到了 N 篇」但链接少，保留已有
        if self.materials_header_re.search(body) and not pairs:
            logger.warning("cend_materials_header_but_no_links platform=%s", self.platform)
        return citations_from_pairs(pairs[:40])

    async def _screenshot(self, page: Any) -> str | None:
        try:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            path = cend_artifact_dir() / f"{self.platform}_{ts}.png"
            await page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            logger.debug("cend_screenshot_failed", exc_info=True)
            return None

    async def capture(self, page: Any, question_text: str, *, brand_list: list[str]) -> CendCaptureResult:
        try:
            await page.goto(self.start_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1200)
            ok_type = await self._type_question(page, question_text)
            if not ok_type:
                return CendCaptureResult(
                    ok=False,
                    platform=self.platform,
                    error="input_not_found",
                    meta={"hint": "检查登录态或更新 input_selectors"},
                )
            await self._wait_answer(page)
            answer = await self._extract_answer_text(page)
            thinking, thinking_ms = await self._extract_thinking(page)
            citations = await self._extract_citations(page)
            hosts = sorted({domain_of(c["url"]) for c in citations if c.get("url")})
            keywords = extract_keywords(answer + "\n" + thinking, brand_list)
            rank_blocks = extract_rank_blocks(answer, brand_list)
            decision_table = extract_decision_table_heuristic(answer)
            artifact = await self._screenshot(page)
            logger.info(
                "cend_capture_ok platform=%s answer_len=%s citations=%s camps=%s",
                self.platform,
                len(answer),
                len(citations),
                len(rank_blocks),
            )
            return CendCaptureResult(
                ok=bool(answer.strip()),
                platform=self.platform,
                answer_text=answer,
                thinking_text=thinking,
                thinking_ms=thinking_ms,
                citations=citations,
                source_hosts=hosts,
                keywords=keywords,
                entities=list(brand_list)[:12],
                rank_blocks=rank_blocks,
                decision_table=decision_table,
                capture_artifact=artifact,
                error=None if answer.strip() else "empty_answer",
                meta={"start_url": self.start_url},
            )
        except Exception as exc:
            logger.warning("cend_capture_failed platform=%s error=%s", self.platform, exc, exc_info=True)
            return CendCaptureResult(ok=False, platform=self.platform, error=str(exc))
