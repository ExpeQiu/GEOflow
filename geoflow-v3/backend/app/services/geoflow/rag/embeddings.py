"""Embedding 客户端。"""

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    async def embed_text(self, text: str) -> list[float] | None:
        if settings.ai_mock_mode:
            # 256 维 mock 向量（生产环境走 OpenAI-compatible API）
            import hashlib

            digest = hashlib.sha256(text.encode()).digest()
            return [((b / 255.0) * 2 - 1) for b in digest] * 12  # 384 dims padded
        # TODO: 从 ai_models 表读取 embedding 模型配置
        return None
