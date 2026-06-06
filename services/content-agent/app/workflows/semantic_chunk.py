"""Semantic chunk planning workflow."""

from __future__ import annotations

import json

from app.workflows.content import _chat


async def run_semantic_chunk_workflow(payload: dict) -> dict:
    knowledge_base_id = int(payload.get("knowledge_base_id") or 0)
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}

    plan_raw = await _chat(
        model,
        "输出 JSON 数组，每项 {\"start_index\":0,\"end_index\":1,\"title\":\"\",\"section_path\":\"\"}",
        json.dumps({"blocks": blocks}, ensure_ascii=False)[:20000],
    )
    plan = _safe_plan(plan_raw)
    chunks = _chunks_from_plan(blocks, plan)

    return {"knowledge_base_id": knowledge_base_id, "chunks": chunks}


def _safe_plan(text: str) -> list:
    text = text.strip().strip("`")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("chunks"), list):
            return parsed["chunks"]
    except json.JSONDecodeError:
        pass
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
