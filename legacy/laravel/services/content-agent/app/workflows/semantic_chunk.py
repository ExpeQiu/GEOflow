"""Semantic chunk workflow — delegates to config-driven graph runner."""

from __future__ import annotations

from app.orchestration.graph_runner import run_configured_workflow


async def run_semantic_chunk_workflow(payload: dict) -> dict:
    return await run_configured_workflow("semantic_chunk", payload)
