"""Execute configured agents against OpenAI-compatible endpoints."""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from app.config.loader import get_agent, load_agents_config

logger = logging.getLogger("content_agent.agent")


async def run_agent(agent_id: str, user_message: str, model: dict | None = None) -> str:
    agent = get_agent(agent_id)
    defaults = load_agents_config().get("defaults", {})
    system_prompt = str(agent.get("system_prompt") or "").strip()
    temperature = float(agent.get("temperature", defaults.get("temperature", 0.7)))
    timeout = float(agent.get("timeout_seconds", defaults.get("timeout_seconds", 120)))
    mock_on_missing = bool(defaults.get("mock_on_missing_credentials", True))

    model = model if isinstance(model, dict) else {}
    base_url = str(model.get("provider_url") or os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    api_key = str(model.get("api_key") or os.getenv("OPENAI_API_KEY") or "")
    model_id = str(model.get("model_id") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini")

    if base_url == "" or api_key == "":
        if mock_on_missing:
            logger.warning("agent_mock_response agent_id=%s", agent_id)
            return _mock_response(agent, user_message)
        raise RuntimeError(f"agent_credentials_missing:{agent_id}")

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        text = str(data["choices"][0]["message"]["content"])
        logger.info("agent_completed agent_id=%s model_id=%s chars=%d", agent_id, model_id, len(text))
        return text


def parse_json_output(text: str, fallback: dict | list | None = None):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError:
        return fallback if fallback is not None else {}


def _mock_response(agent: dict, user_message: str) -> str:
    agent_id = str(agent.get("id") or "")
    output_format = str(agent.get("output_format") or "markdown")
    if output_format == "json":
        if agent_id == "url_keyword_extractor":
            return json.dumps({"keywords": ["示例关键词"]}, ensure_ascii=False)
        if agent_id == "url_title_generator":
            return json.dumps({"titles": ["示例标题"]}, ensure_ascii=False)
        if agent_id == "semantic_chunk_planner":
            return json.dumps([], ensure_ascii=False)
        if agent_id == "url_cleaner":
            return json.dumps({"title": "Mock", "description": "", "text": user_message[:500], "summary": "mock"}, ensure_ascii=False)
        return json.dumps({"summary": "mock", "library_name": "Mock", "knowledge_markdown": user_message[:500]}, ensure_ascii=False)
    return f"# 自动生成草稿\n\n{user_message[:2000]}"
