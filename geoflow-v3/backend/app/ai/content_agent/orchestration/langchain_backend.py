"""LangChain LCEL backend skeleton (未来完整实现)."""

from app.orchestration.langgraph_backend import LangGraphBackend


class LangChainBackend(LangGraphBackend):
    def engine_name(self) -> str:
        return "langchain"
