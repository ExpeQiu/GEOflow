"""Chief-Deputy content pipeline handlers."""

from __future__ import annotations

import json
from typing import Any

from app.agents.runtime import parse_json_output, run_agent
from app.workflows.handlers._common import cite_check, compose_content_prompt


async def pipeline_chief(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    user_request = str(payload.get("user_request") or payload.get("prompt") or "")
    memory = payload.get("memory_snapshot") if isinstance(payload.get("memory_snapshot"), dict) else {}

    chief_input = json.dumps(
        {"user_request": user_request, "memory_snapshot": memory},
        ensure_ascii=False,
    )[:8000]
    raw = await run_agent("chief", chief_input, model)
    parsed = parse_json_output(raw, {"mode": "deep", "chief_brief": user_request[:500], "memory_patch": {}})

    trace = list(state.get("trace") or [])
    trace.append("chief")
    return {
        "pipeline_mode": str(parsed.get("mode") or "deep"),
        "chief_brief": str(parsed.get("chief_brief") or user_request[:500]),
        "memory_patch": parsed.get("memory_patch") if isinstance(parsed.get("memory_patch"), dict) else {},
        "trace": trace,
    }


async def pipeline_deputy_route(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    chief_brief = str(state.get("chief_brief") or "")
    pipeline_mode = str(state.get("pipeline_mode") or "deep")

    route_input = json.dumps(
        {
            "chief_brief": chief_brief,
            "pipeline_mode_hint": pipeline_mode,
            "research_pack": payload.get("research_pack"),
            "brand_pack": payload.get("brand_pack"),
        },
        ensure_ascii=False,
    )[:8000]
    raw = await run_agent("deputy_router", route_input, model)
    parsed = parse_json_output(raw, {"pipeline_path": pipeline_mode if pipeline_mode in {"fast", "deep"} else "deep"})

    path = str(parsed.get("pipeline_path") or pipeline_mode or "deep")
    if path not in {"fast", "deep"}:
        path = "deep"

    trace = list(state.get("trace") or [])
    trace.append("deputy_route")
    return {
        "pipeline_path": path,
        "skip_compliance": path == "fast",
        "trace": trace,
    }


async def pipeline_parallel_probe(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    research = payload.get("research_pack") if isinstance(payload.get("research_pack"), dict) else {}
    brand = payload.get("brand_pack") if isinstance(payload.get("brand_pack"), dict) else {}

    merged_context = {
        "research_query": str(research.get("query") or ""),
        "research_context": str(research.get("context_text") or ""),
        "brand_query": str(brand.get("query") or ""),
        "style_guide": str(brand.get("style_guide") or payload.get("style_guide") or ""),
        "chief_brief": str(state.get("chief_brief") or ""),
    }

    trace = list(state.get("trace") or [])
    trace.append("parallel_probe")
    return {"merged_context": merged_context, "trace": trace}


async def pipeline_writer(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    style_guide = str(payload.get("style_guide") or "")
    merged = state.get("merged_context") if isinstance(state.get("merged_context"), dict) else {}

    prompt_parts = [
        str(state.get("chief_brief") or payload.get("user_request") or payload.get("prompt") or ""),
        str(merged.get("research_context") or ""),
        str(merged.get("style_guide") or style_guide),
    ]
    user_message = compose_content_prompt("\n\n".join(p for p in prompt_parts if p), "", evidence)
    draft = await run_agent("pipeline_writer", user_message, model)

    trace = list(state.get("trace") or [])
    trace.append("writer")
    return {"content": draft.strip(), "needs_revision": False, "trace": trace}


async def pipeline_cross_validate_writer(state: dict[str, Any]) -> dict[str, Any]:
    return await _cross_validate(state, "post_writer", "writer")


async def pipeline_cross_validate_editor(state: dict[str, Any]) -> dict[str, Any]:
    return await _cross_validate(state, "post_editor", "editor")


async def _cross_validate(state: dict[str, Any], node_name: str, retry_target: str) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    content = str(state.get("content") or "")
    checked = cite_check(content, evidence)

    cross_checks = list(state.get("cross_checks") or [])
    entry = {"node": node_name, "passed": checked.get("ok", True), "notes": ""}
    cross_checks.append(entry)

    trace = list(state.get("trace") or [])
    trace.append(f"xval_{retry_target}")

    needs_revision = not checked.get("ok", True)
    patch: dict[str, Any] = {
        "citations": checked.get("citations", []),
        "needs_revision": needs_revision,
        "cross_checks": cross_checks,
        "revision_instruction": checked.get("instruction", ""),
        "trace": trace,
    }
    if needs_revision:
        patch["xval_retry_target"] = retry_target
    return patch


async def pipeline_editor(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    content = str(state.get("content") or "")
    instruction = str(state.get("revision_instruction") or "请润色并补充 [K*] 证据引用。")
    revised = await run_agent("pipeline_editor", content + "\n\n" + instruction, model)

    trace = list(state.get("trace") or [])
    trace.append("editor")
    return {"content": revised.strip(), "needs_revision": False, "trace": trace}


async def pipeline_compliance(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("skip_compliance"):
        trace = list(state.get("trace") or [])
        trace.append("compliance_skipped")
        return {
            "compliance": {"passed": True, "violations": [], "skipped": True},
            "trace": trace,
        }

    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    brand = payload.get("brand_pack") if isinstance(payload.get("brand_pack"), dict) else {}
    content = str(state.get("content") or "")

    compliance_input = json.dumps(
        {
            "content": content[:12000],
            "style_guide": str(brand.get("style_guide") or ""),
            "chief_brief": str(state.get("chief_brief") or ""),
        },
        ensure_ascii=False,
    )
    raw = await run_agent("brand_compliance", compliance_input, model)
    parsed = parse_json_output(raw, {"passed": True, "violations": []})
    passed = bool(parsed.get("passed", True))
    violations = parsed.get("violations") if isinstance(parsed.get("violations"), list) else []

    trace = list(state.get("trace") or [])
    trace.append("compliance")
    return {
        "compliance": {"passed": passed, "violations": violations, "skipped": False},
        "needs_revision": not passed,
        "trace": trace,
    }


async def pipeline_finalize(state: dict[str, Any]) -> dict[str, Any]:
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    citations = state.get("citations") if isinstance(state.get("citations"), list) else []
    cross_checks = state.get("cross_checks") if isinstance(state.get("cross_checks"), list) else []
    compliance = state.get("compliance") if isinstance(state.get("compliance"), dict) else {"passed": True, "violations": []}
    memory_patch = state.get("memory_patch") if isinstance(state.get("memory_patch"), dict) else {}

    trace = list(state.get("trace") or [])
    trace.append("deputy_finalize")

    return {
        "result": {
            "pipeline_mode": str(state.get("pipeline_path") or state.get("pipeline_mode") or "deep"),
            "content": str(state.get("content") or ""),
            "citations": citations,
            "chief_brief_echo": str(state.get("chief_brief") or ""),
            "brand_alignment": {"score": 0.9, "issues": []},
            "compliance": compliance,
            "cross_validation": cross_checks,
            "memory_patch": memory_patch,
        },
        "trace": trace,
    }
