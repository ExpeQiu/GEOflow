"""Content Agent 节点配置 — 读写 agents.yml（system_prompt 等人设）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger("admin.agent_config")

_AGENTS_PATH = Path(__file__).resolve().parents[2] / "ai" / "config" / "agents.yml"
_WORKFLOWS_PATH = Path(__file__).resolve().parents[2] / "ai" / "config" / "workflows.yml"
_CLI_AGENTS_PATH = Path(__file__).resolve().parents[5] / "content-LangGraph-CLI" / "config" / "agents.yml"


class AgentUpdateBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    output_format: str = Field(default="markdown", pattern="^(markdown|json)$")


class _LiteralStr(str):
    """强制 YAML 多行字面量块（|）。"""


def _literal_representer(dumper: yaml.SafeDumper, data: _LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")


yaml.add_representer(_LiteralStr, _literal_representer, Dumper=yaml.SafeDumper)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        logger.warning("agent_config_file_missing", path=str(path))
        return {}
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _prepare_for_dump(data: dict[str, Any]) -> dict[str, Any]:
    """将 system_prompt 转为字面量块，保持 agents.yml 可读性。"""
    out = dict(data)
    agents = out.get("agents")
    if isinstance(agents, dict):
        prepared: dict[str, Any] = {}
        for key, raw in agents.items():
            if not isinstance(raw, dict):
                prepared[key] = raw
                continue
            row = dict(raw)
            prompt = row.get("system_prompt")
            if isinstance(prompt, str) and ("\n" in prompt or len(prompt) > 80):
                row["system_prompt"] = _LiteralStr(prompt if prompt.endswith("\n") else prompt + "\n")
            prepared[key] = row
        out["agents"] = prepared
    return out


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.dump(
        _prepare_for_dump(data),
        Dumper=yaml.SafeDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
    path.write_text(text, encoding="utf-8")
    logger.info("agent_config_written", path=str(path))


def _agent_usage_map() -> dict[str, list[dict[str, str]]]:
    """agent_id -> [{workflow, node_id}]"""
    data = _read_yaml(_WORKFLOWS_PATH)
    usage: dict[str, list[dict[str, str]]] = {}
    for wf_key, wf in (data.get("workflows") or {}).items():
        if not isinstance(wf, dict):
            continue
        for node in wf.get("nodes") or []:
            if not isinstance(node, dict) or node.get("type") != "agent":
                continue
            agent_id = str(node.get("agent") or "").strip()
            if not agent_id:
                continue
            usage.setdefault(agent_id, []).append(
                {"workflow": str(wf_key), "node_id": str(node.get("id") or "")}
            )
    return usage


def _invalidate_runtime_cache() -> None:
    """清除 content-agent 运行时 lru_cache（含侧车挂载后的 app.config.loader）。"""
    cleared = False
    for mod_name in ("app.config.loader", "app.ai.content_agent.config.loader"):
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        fn = getattr(mod, "invalidate_agents_config_cache", None)
        if callable(fn):
            fn()
            cleared = True
            continue
        load_fn = getattr(mod, "load_agents_config", None)
        if load_fn is not None and hasattr(load_fn, "cache_clear"):
            load_fn.cache_clear()
            cleared = True
    if not cleared:
        try:
            from app.ai.content_agent.config import loader as ca_loader

            ca_loader.invalidate_agents_config_cache()
            cleared = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent_config_cache_invalidate_skipped", err=str(exc))
    logger.info("agent_config_cache_invalidate", done=cleared)


def list_agents() -> dict:
    data = _read_yaml(_AGENTS_PATH)
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    agents = data.get("agents") if isinstance(data.get("agents"), dict) else {}
    usage = _agent_usage_map()
    items = []
    for agent_id, raw in agents.items():
        if not isinstance(raw, dict):
            continue
        prompt = str(raw.get("system_prompt") or "")
        items.append(
            {
                "id": agent_id,
                "name": str(raw.get("name") or agent_id),
                "system_prompt": prompt,
                "system_prompt_preview": prompt[:120].replace("\n", " "),
                "temperature": float(raw.get("temperature", defaults.get("temperature", 0.7))),
                "output_format": str(raw.get("output_format") or "markdown"),
                "used_by": usage.get(agent_id, []),
            }
        )
    items.sort(key=lambda x: x["id"])
    logger.info("agent_config_listed", count=len(items), path=str(_AGENTS_PATH))
    return {
        "config_path": str(_AGENTS_PATH),
        "defaults": {
            "temperature": float(defaults.get("temperature", 0.7)),
            "timeout_seconds": int(defaults.get("timeout_seconds", 120)),
            "mock_on_missing_credentials": bool(defaults.get("mock_on_missing_credentials", True)),
        },
        "items": items,
    }


def get_agent(agent_id: str) -> dict:
    data = _read_yaml(_AGENTS_PATH)
    agents = data.get("agents") if isinstance(data.get("agents"), dict) else {}
    raw = agents.get(agent_id)
    if not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="agent_not_found")
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    usage = _agent_usage_map()
    prompt = str(raw.get("system_prompt") or "")
    return {
        "item": {
            "id": agent_id,
            "name": str(raw.get("name") or agent_id),
            "system_prompt": prompt,
            "temperature": float(raw.get("temperature", defaults.get("temperature", 0.7))),
            "output_format": str(raw.get("output_format") or "markdown"),
            "used_by": usage.get(agent_id, []),
        }
    }


def update_agent(agent_id: str, body: AgentUpdateBody) -> dict:
    data = _read_yaml(_AGENTS_PATH)
    agents = data.setdefault("agents", {})
    if not isinstance(agents, dict) or agent_id not in agents or not isinstance(agents[agent_id], dict):
        raise HTTPException(status_code=404, detail="agent_not_found")

    agents[agent_id]["name"] = body.name.strip()
    agents[agent_id]["system_prompt"] = body.system_prompt.strip()
    agents[agent_id]["temperature"] = body.temperature
    agents[agent_id]["output_format"] = body.output_format

    _write_yaml(_AGENTS_PATH, data)
    if _CLI_AGENTS_PATH.is_file():
        try:
            cli_data = _read_yaml(_CLI_AGENTS_PATH)
            cli_agents = cli_data.setdefault("agents", {})
            if isinstance(cli_agents, dict) and agent_id in cli_agents and isinstance(cli_agents[agent_id], dict):
                cli_agents[agent_id]["name"] = body.name.strip()
                cli_agents[agent_id]["system_prompt"] = body.system_prompt.strip()
                cli_agents[agent_id]["temperature"] = body.temperature
                cli_agents[agent_id]["output_format"] = body.output_format
                _write_yaml(_CLI_AGENTS_PATH, cli_data)
                logger.info("agent_config_cli_synced", agent_id=agent_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent_config_cli_sync_failed", agent_id=agent_id, err=str(exc))

    _invalidate_runtime_cache()
    logger.info("agent_config_updated", agent_id=agent_id)
    return get_agent(agent_id)
