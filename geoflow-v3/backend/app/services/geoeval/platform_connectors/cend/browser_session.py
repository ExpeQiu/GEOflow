"""Playwright 会话：持久 Profile，人工扫码登录后复用。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def cend_profile_dir(platform: str) -> Path:
    root = os.getenv(
        "CEND_PROFILE_ROOT",
        str(Path.home() / "Library" / "Application Support" / "geoflow-cend"),
    )
    path = Path(root) / platform
    path.mkdir(parents=True, exist_ok=True)
    return path


def cend_artifact_dir() -> Path:
    root = os.getenv(
        "CEND_ARTIFACT_ROOT",
        str(Path.home() / "Library" / "Application Support" / "geoflow-cend" / "artifacts"),
    )
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def launch_persistent_context(platform: str, *, headless: bool | None = None) -> Any:
    """返回 Playwright BrowserContext；调用方负责关闭。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("playwright_not_installed") from exc

    if headless is None:
        headless = os.getenv("CEND_HEADLESS", "true").lower() in ("1", "true", "yes")

    user_data = str(cend_profile_dir(platform))
    logger.info("cend_launch_profile platform=%s user_data=%s headless=%s", platform, user_data, headless)
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data,
        headless=headless,
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
        args=["--disable-blink-features=AutomationControlled"],
    )
    # 挂在 context 上便于关闭时 stop playwright
    context._geoflow_pw = pw  # type: ignore[attr-defined]
    return context


async def close_context(context: Any) -> None:
    pw = getattr(context, "_geoflow_pw", None)
    try:
        await context.close()
    except Exception:
        logger.debug("cend_context_close_failed", exc_info=True)
    if pw is not None:
        try:
            await pw.stop()
        except Exception:
            logger.debug("cend_playwright_stop_failed", exc_info=True)


async def check_profile_ready(platform: str, login_selector: str | None = None) -> dict:
    """快速打开起始页，检测是否仍需登录。"""
    from app.services.geoeval.platform_connectors.base import CEND_PLATFORM_URLS

    url = CEND_PLATFORM_URLS.get(platform)
    if not url:
        return {"ok": False, "reason": "unknown_platform"}
    try:
        context = await launch_persistent_context(platform, headless=True)
    except RuntimeError as exc:
        return {"ok": False, "reason": str(exc)}
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)
        body = (await page.content())[:8000].lower()
        login_hints = ("扫码", "登录", "login", "qrcode", "请登录")
        needs_login = any(h.lower() in body for h in login_hints)
        if login_selector:
            try:
                el = await page.query_selector(login_selector)
                if el:
                    needs_login = True
            except Exception:
                pass
        logger.info("cend_profile_check platform=%s needs_login=%s", platform, needs_login)
        return {"ok": not needs_login, "needs_login": needs_login, "platform": platform, "url": url}
    except Exception as exc:
        logger.warning("cend_profile_check_failed platform=%s error=%s", platform, exc)
        return {"ok": False, "reason": str(exc), "platform": platform}
    finally:
        await close_context(context)
