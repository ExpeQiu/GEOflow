"""LangGraph workflow 同步运行器 — 内嵌 content-agent。"""

import asyncio
import importlib
import re
import sys
import types
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ai.workflow")
settings = get_settings()

_CA_ROOT = Path(__file__).resolve().parent / "content_agent"
_CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _ensure_content_agent_app_package() -> None:
    """将 content_agent 目录挂载为顶层 app 包（兼容原侧车 import 路径）。"""
    if "app" in sys.modules and hasattr(sys.modules["app"], "__geoflow_ca__"):
        return
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [str(_CA_ROOT)]  # type: ignore[attr-defined]
    app_pkg.__geoflow_ca__ = True  # type: ignore[attr-defined]
    sys.modules["app"] = app_pkg
    import os

    os.environ.setdefault("CONTENT_AGENT_CONFIG_DIR", str(_CONFIG_DIR))


def run_workflow_sync(workflow_type: str, payload: dict) -> dict:
    if settings.ai_mock_mode:
        return _mock_result(workflow_type, payload)

    try:
        _ensure_content_agent_app_package()
        graph_runner = importlib.import_module("app.orchestration.graph_runner")
        run_fn = graph_runner.run_configured_workflow
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    raw = pool.submit(asyncio.run, run_fn(workflow_type, payload)).result()
            else:
                raw = loop.run_until_complete(run_fn(workflow_type, payload))
        except RuntimeError:
            raw = asyncio.run(run_fn(workflow_type, payload))
        return _normalize_workflow_result(workflow_type, raw, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("workflow_fallback_mock", workflow=workflow_type, error=str(exc))
        return _mock_result(workflow_type, payload)


def _normalize_workflow_result(workflow_type: str, raw: dict, payload: dict) -> dict:
    """将 LangGraph 输出归一化为与 mock 一致的契约。"""
    if not isinstance(raw, dict):
        raw = {}

    if workflow_type == "url_import":
        page = payload.get("page_json") if isinstance(payload.get("page_json"), dict) else {}
        url = str(payload.get("url") or page.get("url") or "")
        text_fallback = str(page.get("text") or page.get("title") or url)[:6000]
        title_fallback = str(page.get("title") or "导入知识库")
        keywords = raw.get("keywords") if isinstance(raw.get("keywords"), list) else _extract_keywords(text_fallback)
        titles = raw.get("titles") if isinstance(raw.get("titles"), list) else []
        knowledge_md = str(raw.get("knowledge_markdown") or text_fallback)
        return {
            "summary": str(raw.get("summary") or knowledge_md[:280] or f"从 {url} 导入"),
            "library_name": str(raw.get("library_name") or title_fallback),
            "keywords": [str(k) for k in keywords if str(k).strip()][:30],
            "titles": [str(t) for t in titles if str(t).strip()][:50],
            "knowledge_markdown": knowledge_md,
            "analysis_source": str(raw.get("analysis_source") or "ai"),
            "engine": str(raw.get("engine") or "langgraph"),
        }

    return raw if raw else _mock_result(workflow_type, payload)


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}", text)
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
        if len(out) >= limit:
            break
    return out


def _mock_result(workflow_type: str, payload: dict) -> dict:
    if workflow_type == "url_import":
        page = payload.get("page_json") if isinstance(payload.get("page_json"), dict) else {}
        text = str(page.get("text") or page.get("title") or payload.get("url", ""))[:6000]
        title = str(page.get("title") or "导入知识库")
        keywords = _extract_keywords(text)
        return {
            "summary": text[:280] or f"从 {payload.get('url', 'URL')} 导入",
            "library_name": title,
            "keywords": keywords,
            "titles": [f"{title} · 深度解读", f"{title} · 核心要点", f"{title} · 行业趋势"][: max(3, min(5, len(keywords) + 2))],
            "knowledge_markdown": f"# {title}\n\n{text[:4000]}\n\n> 来源：{payload.get('url', 'inline')}",
            "analysis_source": "mock",
            "engine": "mock",
        }

    if workflow_type == "semantic_chunk":
        content = str(payload.get("content") or "")[:2000]
        return {
            "chunks": [{"index": 0, "content": content[:800]}, {"index": 1, "content": content[800:1600]}],
            "engine": "mock",
        }

    prompt = payload.get("prompt", "")[:80]
    title = str(payload.get("title") or payload.get("user_request") or f"Mock: {workflow_type}")
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    evidence_lines: list[str] = []
    for item in evidence[:5]:
        if not isinstance(item, dict):
            continue
        eid = item.get("id") or item.get("chunk_id") or "?"
        body = str(item.get("content") or "").strip()
        if not body:
            continue
        evidence_lines.append(f"[{eid}] {body[:500]}")
    evidence_block = ""
    if evidence_lines:
        evidence_block = "\n\n## 依据知识库\n\n" + "\n\n".join(evidence_lines)
    content = f"# {title}\n\n{prompt}{evidence_block}\n\n> Generated by GEOFlow v3 mock mode."
    return {
        "content": content,
        "title": title,
        "citations": evidence[:3],
        "engine": "mock",
    }
