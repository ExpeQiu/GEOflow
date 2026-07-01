"""Compile and run workflows from workflows.yml (LangGraph or linear fallback)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config.loader import config_dir, get_workflow
from app.workflows.handlers import HANDLERS

logger = logging.getLogger("content_agent.graph")

TERMINAL_NODES = {"finalize", "build_chunks", "deputy_finalize"}
_compiled_cache: dict[str, Any] = {}


async def run_configured_workflow(workflow_type: str, payload: dict) -> dict:
    workflow = get_workflow(workflow_type)
    initial_state: dict[str, Any] = {"payload": payload, "trace": []}

    if _langgraph_available():
        try:
            final_state = await _run_langgraph(workflow_type, workflow, initial_state)
            logger.info("workflow_completed engine=langgraph workflow=%s steps=%s", workflow_type, final_state.get("trace"))
            return _extract_result(workflow_type, final_state)
        except Exception as exc:  # noqa: BLE001
            logger.warning("langgraph_fallback workflow=%s error=%s", workflow_type, exc)

    final_state = await _run_linear(workflow, initial_state)
    logger.info("workflow_completed engine=linear workflow=%s steps=%s", workflow_type, final_state.get("trace"))
    return _extract_result(workflow_type, final_state)


def _langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401

        return True
    except ImportError:
        return False


def _config_cache_key(workflow_type: str) -> str:
    base = config_dir()
    mtimes = []
    for name in ("workflows.yml", "agents.yml"):
        path = base / name
        mtimes.append(str(path.stat().st_mtime) if path.is_file() else "0")
    return f"{workflow_type}:{'|'.join(mtimes)}"


def _get_compiled_graph(workflow_type: str, workflow: dict[str, Any]):
    from langgraph.graph import END, StateGraph

    cache_key = _config_cache_key(workflow_type)
    cached = _compiled_cache.get(cache_key)
    if cached is not None:
        logger.debug("graph_compiled_cache_hit workflow=%s", workflow_type)
        return cached

    graph = StateGraph(dict)
    node_ids: list[str] = []

    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "")
        handler_name = str(node.get("handler") or node_id)
        handler = HANDLERS.get(handler_name)
        if handler is None:
            raise RuntimeError(f"handler_not_found:{handler_name}")
        graph.add_node(node_id, handler)
        node_ids.append(node_id)

    edges = [edge for edge in workflow.get("edges", []) if isinstance(edge, dict)]
    conditional_sources: dict[str, list[dict[str, Any]]] = {}

    for edge in edges:
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if src == "__start__":
            graph.set_entry_point(dst)
            continue
        if edge.get("when"):
            conditional_sources.setdefault(src, []).append(edge)
            continue
        if dst:
            graph.add_edge(src, dst)

    for src, conditional_edges in conditional_sources.items():
        route_map = {str(edge.get("to") or ""): str(edge.get("to") or "") for edge in conditional_edges}
        graph.add_conditional_edges(src, _make_conditional_router(conditional_edges), route_map)

    for terminal in TERMINAL_NODES:
        if terminal in node_ids:
            graph.add_edge(terminal, END)

    compiled = graph.compile()
    _compiled_cache[cache_key] = compiled
    logger.info("graph_compiled_cache_miss workflow=%s key=%s", workflow_type, cache_key)
    return compiled


def _matches_when(when: str, state: dict[str, Any]) -> bool:
    if when == "needs_revision":
        return bool(state.get("needs_revision"))
    if when == "ok":
        return not state.get("needs_revision") and not state.get("skip_compliance")
    if when == "skip_compliance":
        return bool(state.get("skip_compliance")) and not state.get("needs_revision")
    if when == "fast_mode":
        return str(state.get("pipeline_path") or "") == "fast"
    if when == "deep_mode":
        return str(state.get("pipeline_path") or "") == "deep"
    compliance = state.get("compliance") if isinstance(state.get("compliance"), dict) else {}
    if when == "compliance_pass":
        return bool(compliance.get("passed"))
    if when == "compliance_reject":
        return compliance.get("passed") is False
    return False


def _make_conditional_router(conditional_edges: list[dict[str, Any]]):
    def router(state: dict[str, Any]) -> str:
        for edge in conditional_edges:
            when = str(edge.get("when") or "")
            if _matches_when(when, state):
                return str(edge.get("to") or "")
        return str(conditional_edges[-1].get("to") or "")

    return router


async def _run_langgraph(workflow_type: str, workflow: dict[str, Any], initial_state: dict[str, Any]) -> dict[str, Any]:
    compiled = _get_compiled_graph(workflow_type, workflow)
    return await compiled.ainvoke(initial_state)


async def _run_linear(workflow: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    nodes = {node["id"]: node for node in workflow.get("nodes", []) if isinstance(node, dict) and node.get("id")}
    edges = [edge for edge in workflow.get("edges", []) if isinstance(edge, dict)]

    start_edges = [edge for edge in edges if edge.get("from") == "__start__"]
    if not start_edges:
        raise RuntimeError("workflow_missing_start_edge")

    current = str(start_edges[0].get("to"))
    visited_guard = 0

    while current and visited_guard < 32:
        visited_guard += 1
        node = nodes.get(current)
        if not node:
            break

        handler_name = str(node.get("handler") or current)
        handler = HANDLERS.get(handler_name)
        if handler is None:
            raise RuntimeError(f"handler_not_found:{handler_name}")

        patch = await handler(state)
        if isinstance(patch, dict):
            state.update(patch)

        if current in TERMINAL_NODES:
            break

        next_nodes = _resolve_next_nodes(current, edges, state)
        if not next_nodes:
            break
        current = next_nodes[0]

    return state


def _resolve_next_nodes(current: str, edges: list[dict[str, Any]], state: dict[str, Any]) -> list[str]:
    candidates = [edge for edge in edges if str(edge.get("from") or "") == current]
    if not candidates:
        return []

    conditional = [edge for edge in candidates if edge.get("when")]
    if conditional:
        for edge in conditional:
            when = str(edge.get("when") or "")
            if _matches_when(when, state):
                return [str(edge.get("to") or "")]
        return []

    return [str(candidates[0].get("to") or "")]


def _extract_result(workflow_type: str, state: dict[str, Any]) -> dict:
    if isinstance(state.get("result"), dict):
        result = dict(state["result"])
        if state.get("trace"):
            result["trace"] = {"steps": list(state["trace"])}
        return result

    if workflow_type in {"content", "content_pipeline"}:
        return {
            "content": str(state.get("content") or ""),
            "citations": state.get("citations") if isinstance(state.get("citations"), list) else [],
            "trace": {"steps": list(state.get("trace") or [])},
        }

    return {"trace": {"steps": list(state.get("trace") or [])}}
