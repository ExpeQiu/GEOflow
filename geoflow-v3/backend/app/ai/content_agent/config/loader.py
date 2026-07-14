"""Load agents.yml and workflows.yml."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("content_agent.config")


def config_dir() -> Path:
    override = os.getenv("CONTENT_AGENT_CONFIG_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "config"


@lru_cache(maxsize=1)
def load_agents_config() -> dict[str, Any]:
    path = config_dir() / "agents.yml"
    data = _read_yaml(path)
    logger.info("agents_config_loaded path=%s agents=%d", path, len(data.get("agents", {})))
    return data


@lru_cache(maxsize=1)
def load_workflows_config() -> dict[str, Any]:
    path = config_dir() / "workflows.yml"
    data = _read_yaml(path)
    logger.info("workflows_config_loaded path=%s workflows=%d", path, len(data.get("workflows", {})))
    return data


def invalidate_agents_config_cache() -> None:
    load_agents_config.cache_clear()
    logger.info("agents_config_cache_cleared")


def invalidate_workflows_config_cache() -> None:
    load_workflows_config.cache_clear()
    logger.info("workflows_config_cache_cleared")


def get_agent(agent_id: str) -> dict[str, Any]:
    agents = load_agents_config().get("agents", {})
    if agent_id not in agents:
        raise KeyError(f"agent_not_found:{agent_id}")
    defaults = load_agents_config().get("defaults", {})
    merged = {**defaults, **agents[agent_id]}
    merged["id"] = agent_id
    return merged


def get_workflow(workflow_type: str) -> dict[str, Any]:
    workflows = load_workflows_config().get("workflows", {})
    if workflow_type not in workflows:
        raise KeyError(f"workflow_not_found:{workflow_type}")
    return workflows[workflow_type]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        logger.warning("config_file_missing path=%s", path)
        return {}
    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)
    return parsed if isinstance(parsed, dict) else {}
