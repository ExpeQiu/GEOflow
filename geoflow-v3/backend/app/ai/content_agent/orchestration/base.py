"""Orchestration backend protocol."""

from typing import Protocol


class OrchestrationBackend(Protocol):
    async def run_workflow(self, workflow_type: str, payload: dict, request_id: str) -> dict: ...

    def engine_name(self) -> str: ...
