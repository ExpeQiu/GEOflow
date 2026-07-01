"""Shared handler utilities."""

from __future__ import annotations

from typing import Any


def compose_content_prompt(prompt: str, style_guide: str, evidence: list) -> str:
    parts = [prompt]
    if style_guide:
        parts.append(style_guide)
    if evidence:
        parts.append(
            "参考证据:\n"
            + "\n".join(f"[{e.get('id')}]\n{e.get('content')}" for e in evidence if isinstance(e, dict))
        )
    return "\n\n".join(parts)


def cite_check(content: str, evidence: list) -> dict[str, Any]:
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
