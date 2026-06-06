"""Content workflow."""

from __future__ import annotations

import os

import httpx


async def run_content_workflow(payload: dict) -> dict:
    prompt = str(payload.get("prompt") or "")
    style_guide = str(payload.get("style_guide") or "")
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}

    draft = await _chat(
        model,
        "你是专业中文写作助手，请输出高质量 Markdown 文章。",
        _compose_prompt(prompt, style_guide, evidence),
    )
    checked = _cite_check(draft, evidence)
    if not checked["ok"]:
        draft = await _chat(
            model,
            "你是专业编辑，请补充 [K*] 证据引用后输出 Markdown。",
            draft + "\n\n" + checked["instruction"],
        )

    return {
        "content": draft.strip(),
        "citations": checked.get("citations", []),
        "trace": {"steps": ["draft", "cite_check", "finalize"]},
    }


def _compose_prompt(prompt: str, style_guide: str, evidence: list) -> str:
    parts = [prompt]
    if style_guide:
        parts.append(style_guide)
    if evidence:
        parts.append("参考证据:\n" + "\n".join(f"[{e.get('id')}]\n{e.get('content')}" for e in evidence if isinstance(e, dict)))
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


async def _chat(model: dict, system: str, user: str) -> str:
    base_url = str(model.get("provider_url") or os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    api_key = str(model.get("api_key") or os.getenv("OPENAI_API_KEY") or "")
    model_id = str(model.get("model_id") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini")
    if base_url == "" or api_key == "":
        return f"# 自动生成草稿\n\n{user[:2000]}"

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])
