"""Backend factory."""

import os

from app.orchestration.langchain_backend import LangChainBackend
from app.orchestration.langgraph_backend import LangGraphBackend


def create_backend():
    driver = os.getenv("CONTENT_AGENT_DRIVER", "langgraph").strip().lower()
    if driver == "langchain":
        return LangChainBackend()
    return LangGraphBackend()
