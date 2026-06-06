"""Workflow node handlers referenced by workflows.yml."""

from __future__ import annotations

import json
from typing import Any

from app.agents.runtime import parse_json_output, run_agent


async def content_draft(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    prompt = str(payload.get("prompt") or "")
    style_guide = str(payload.get("style_guide") or "")
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}

    user_message = _compose_content_prompt(prompt, style_guide, evidence)
    draft = await run_agent("content_drafter", user_message, model)
    trace = list(state.get("trace") or [])
    trace.append("draft")
    return {"content": draft.strip(), "trace": trace}


async def cite_check(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    content = str(state.get("content") or "")
    checked = _cite_check(content, evidence)
    trace = list(state.get("trace") or [])
    trace.append("cite_check")
    return {
        "citations": checked.get("citations", []),
        "needs_revision": not checked.get("ok", True),
        "revision_instruction": checked.get("instruction", ""),
        "trace": trace,
    }


async def content_revise(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    content = str(state.get("content") or "")
    instruction = str(state.get("revision_instruction") or "请在正文中标注 [K1] 等证据编号。")
    revised = await run_agent("content_editor", content + "\n\n" + instruction, model)
    trace = list(state.get("trace") or [])
    trace.append("revise")
    return {"content": revised.strip(), "trace": trace}


async def content_finalize(state: dict[str, Any]) -> dict[str, Any]:
    trace = list(state.get("trace") or [])
    trace.append("finalize")
    return {"trace": trace}


async def url_clean_page(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    page_json = payload.get("page_json") if isinstance(payload.get("page_json"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    clean_raw = await run_agent("url_cleaner", json.dumps(page_json, ensure_ascii=False), model)
    cleaned = parse_json_output(clean_raw, page_json)
    trace = list(state.get("trace") or [])
    trace.append("clean_page")
    return {"cleaned": cleaned, "trace": trace}


async def url_build_knowledge(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    page_json = payload.get("page_json") if isinstance(payload.get("page_json"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    cleaned = state.get("cleaned") if isinstance(state.get("cleaned"), dict) else {}
    knowledge_raw = await run_agent(
        "url_knowledge_builder",
        json.dumps({"page": page_json, "cleaned": cleaned}, ensure_ascii=False),
        model,
    )
    knowledge = parse_json_output(knowledge_raw, {})
    knowledge_md = str(knowledge.get("knowledge_markdown") or cleaned.get("text") or "")
    trace = list(state.get("trace") or [])
    trace.append("build_knowledge")
    return {"knowledge": knowledge, "knowledge_markdown": knowledge_md, "trace": trace}


async def url_extract_keywords(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    knowledge_md = str(state.get("knowledge_markdown") or "")
    keywords_raw = await run_agent("url_keyword_extractor", knowledge_md[:4000], model)
    keywords_payload = parse_json_output(keywords_raw, {"keywords": []})
    keywords = [str(k) for k in keywords_payload.get("keywords", []) if str(k).strip()][:10]
    trace = list(state.get("trace") or [])
    trace.append("extract_keywords")
    return {"keywords": keywords, "trace": trace}


async def url_extract_titles(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    keywords = state.get("keywords") if isinstance(state.get("keywords"), list) else []
    titles_raw = await run_agent("url_title_generator", "关键词：" + "、".join(str(k) for k in keywords), model)
    titles_payload = parse_json_output(titles_raw, {"titles": []})
    titles = [str(t) for t in titles_payload.get("titles", []) if str(t).strip()][:50]
    trace = list(state.get("trace") or [])
    trace.append("extract_titles")
    return {"titles": titles, "trace": trace}


async def url_finalize(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    model_id = int(payload.get("ai_model_id") or 0)
    cleaned = state.get("cleaned") if isinstance(state.get("cleaned"), dict) else {}
    knowledge = state.get("knowledge") if isinstance(state.get("knowledge"), dict) else {}
    trace = list(state.get("trace") or [])
    trace.append("finalize")
    return {
        "result": {
            "summary": str(knowledge.get("summary") or cleaned.get("summary") or ""),
            "library_name": str(knowledge.get("library_name") or cleaned.get("title") or "导入知识库"),
            "keywords": state.get("keywords") or [],
            "titles": state.get("titles") or [],
            "knowledge_markdown": str(state.get("knowledge_markdown") or ""),
            "analysis_source": "ai",
            "model": {"id": model_id, "name": str(model.get("name") or model_id)},
        },
        "trace": trace,
    }


async def semantic_plan_blocks(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    plan_raw = await run_agent(
        "semantic_chunk_planner",
        json.dumps({"blocks": blocks}, ensure_ascii=False)[:20000],
        model,
    )
    plan = _safe_plan(plan_raw)
    trace = list(state.get("trace") or [])
    trace.append("plan_blocks")
    return {"plan": plan, "trace": trace}


async def semantic_build_chunks(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    knowledge_base_id = int(payload.get("knowledge_base_id") or 0)
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    plan = state.get("plan") if isinstance(state.get("plan"), list) else []
    chunks = _chunks_from_plan(blocks, plan)
    trace = list(state.get("trace") or [])
    trace.append("build_chunks")
    return {
        "result": {"knowledge_base_id": knowledge_base_id, "chunks": chunks},
        "trace": trace,
    }


def _compose_content_prompt(prompt: str, style_guide: str, evidence: list) -> str:
    parts = [prompt]
    if style_guide:
        parts.append(style_guide)
    if evidence:
        parts.append(
            "参考证据:\n"
            + "\n".join(f"[{e.get('id')}]\n{e.get('content')}" for e in evidence if isinstance(e, dict))
        )
    return "\n\n".join(parts)


def _cite_check(content: str, evidence: list) -> dict:
    if not evidence:
        return {"ok": True, "citations": []}
    citations = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "")
        if cid and f"[{cid}]" in content:
            citations.append(cid)
    ok = len(citations) > 0 or len(evidence) == 0
    return {
        "ok": ok,
        "citations": citations,
        "instruction": "请在正文中标注 [K1] 等证据编号。",
    }


def _safe_plan(text: str) -> list:
    parsed = parse_json_output(text, [])
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and isinstance(parsed.get("chunks"), list):
        return parsed["chunks"]
    return []


def _chunks_from_plan(blocks: list, plan: list) -> list:
    if not blocks:
        return []
    if not plan:
        return [
            {
                "content": "\n\n".join(str(b.get("text") or "") for b in blocks if isinstance(b, dict)),
                "title": "",
                "section_path": "",
                "strategy": "semantic",
                "metadata": {},
            }
        ]

    chunks = []
    for item in plan:
        if not isinstance(item, dict):
            continue
        start = max(0, int(item.get("start_index") or 0))
        end = min(len(blocks) - 1, int(item.get("end_index") or start))
        slice_blocks = blocks[start : end + 1]
        content = "\n\n".join(str(b.get("text") or "") for b in slice_blocks if isinstance(b, dict)).strip()
        if content == "":
            continue
        chunks.append(
            {
                "content": content,
                "title": str(item.get("title") or ""),
                "section_path": str(item.get("section_path") or ""),
                "strategy": "semantic",
                "metadata": {},
            }
        )
    return chunks


HANDLERS: dict[str, Any] = {
    "content_draft": content_draft,
    "cite_check": cite_check,
    "content_revise": content_revise,
    "content_finalize": content_finalize,
    "url_clean_page": url_clean_page,
    "url_build_knowledge": url_build_knowledge,
    "url_extract_keywords": url_extract_keywords,
    "url_extract_titles": url_extract_titles,
    "url_finalize": url_finalize,
    "semantic_plan_blocks": semantic_plan_blocks,
    "semantic_build_chunks": semantic_build_chunks,
}
