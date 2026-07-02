"""URL 页面抓取与简易正文提取。"""

import re

import httpx

from app.core.logging import get_logger

logger = get_logger("geoflow.url_fetch")


def fetch_page_json(url: str) -> dict:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url)
    html = resp.text or ""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else url
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()[:12000]
    logger.info("url_fetched url=%s status=%s chars=%s", url[:80], resp.status_code, len(text))
    return {
        "url": url,
        "title": title,
        "text": text,
        "status_code": resp.status_code,
        "content_type": resp.headers.get("content-type", ""),
    }
