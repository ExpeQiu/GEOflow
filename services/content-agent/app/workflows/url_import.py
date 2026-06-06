"""URL import workflow."""

from __future__ import annotations

import json

from app.workflows.content import _chat


async def run_url_import_workflow(payload: dict) -> dict:
    page_json = payload.get("page_json") if isinstance(payload.get("page_json"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    model_id = int(payload.get("ai_model_id") or 0)

    clean_raw = await _chat(
        model,
        "输出 JSON：{\"title\":\"\",\"description\":\"\",\"text\":\"\",\"summary\":\"\"}",
        json.dumps(page_json, ensure_ascii=False),
    )
    cleaned = _safe_json(clean_raw, page_json)

    knowledge_raw = await _chat(
        model,
        "输出 JSON：{\"summary\":\"\",\"library_name\":\"\",\"knowledge_markdown\":\"\"}",
        json.dumps({"page": page_json, "cleaned": cleaned}, ensure_ascii=False),
    )
    knowledge = _safe_json(knowledge_raw, {})
    knowledge_md = str(knowledge.get("knowledge_markdown") or cleaned.get("text") or "")

    keywords_raw = await _chat(
        model,
        "输出 JSON：{\"keywords\":[\"...\"]}",
        knowledge_md[:4000],
    )
    keywords_payload = _safe_json(keywords_raw, {"keywords": []})
    keywords = [str(k) for k in keywords_payload.get("keywords", []) if str(k).strip()][:10]

    titles_raw = await _chat(
        model,
        "输出 JSON：{\"titles\":[\"...\"]}",
        "关键词：" + "、".join(keywords),
    )
    titles_payload = _safe_json(titles_raw, {"titles": []})
    titles = [str(t) for t in titles_payload.get("titles", []) if str(t).strip()][:50]

    return {
        "summary": str(knowledge.get("summary") or cleaned.get("summary") or ""),
        "library_name": str(knowledge.get("library_name") or cleaned.get("title") or "导入知识库"),
        "keywords": keywords,
        "titles": titles,
        "knowledge_markdown": knowledge_md,
        "analysis_source": "ai",
        "model": {"id": model_id, "name": str(model.get("name") or model_id)},
    }


def _safe_json(text: str, fallback: dict) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else fallback
    except json.JSONDecodeError:
        return fallback
