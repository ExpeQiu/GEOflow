"""GEO 答案审计 — LLM 评估文章 AI 可见性。"""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.material import AiModel
from app.services.geoflow.llm_client import chat_json
from app.services.geoeval.platform_connectors.corpus_connector import _tokenize

logger = logging.getLogger(__name__)

AUDIT_SYSTEM = (
    "你是 GEO 内容审计员。对比「待评估文章」与「模拟 RAG 回答」，判断文章是否具备 AI 搜索可见性。"
    "检查：是否直接回答用户问题、是否有结构化信息、是否与模拟回答/语料一致、是否有明确实体信息。"
    '返回 JSON：{"audit_passed": bool, "audit_score": 0.0-1.0, '
    '"checks": {"answers_query": bool, "structured": bool, "grounded": bool, "entity_clear": bool}, '
    '"failures": ["简短原因"]}'
)


def _bigrams(text: str) -> set[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", text)
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def _answers_query(query: str, content: str) -> bool:
    if len(_tokenize(query) & _tokenize(content)) >= 1:
        return True
    return len(_bigrams(query) & _bigrams(content)) >= 2


def _has_structure(content: str) -> bool:
    if re.search(r"^#{1,3}\s", content, re.MULTILINE):
        return True
    if content.count("|") >= 2:
        return True
    if re.search(r"^[\-*\d+\.]+\s", content, re.MULTILINE):
        return True
    return False


def _mock_audit(article: Article, simulation: dict) -> dict:
    content = article.content or ""
    query = simulation.get("query") or article.title
    failures: list[str] = []

    answers_query = _answers_query(query, content)
    structured = _has_structure(content)
    grounded = float(simulation.get("retrieval_score") or 0) >= 0.15 or bool(simulation.get("article_in_retrieval"))
    entity_clear = len(content) >= 180 and bool(article.title.strip())

    checks = {
        "answers_query": answers_query,
        "structured": structured,
        "grounded": grounded,
        "entity_clear": entity_clear,
    }
    if not answers_query:
        failures.append("未直接回应检索问题")
    if not structured:
        failures.append("缺少结构化呈现（标题/列表/表格）")
    if not grounded:
        failures.append("与知识库召回语料关联弱")
    if not entity_clear:
        failures.append("正文过短或主题不明确")

    passed_count = sum(1 for v in checks.values() if v)
    audit_score = round(passed_count / len(checks), 4)
    audit_passed = passed_count >= 3 and float(simulation.get("simulation_score") or 0) >= 0.35

    return {
        "audit_passed": audit_passed,
        "audit_score": audit_score,
        "checks": checks,
        "failures": failures,
        "engine": "mock",
    }


class AnswerAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def audit(
        self,
        article: Article,
        simulation: dict,
        *,
        model: AiModel | None,
    ) -> dict:
        use_llm = model is not None and not self.settings.ai_mock_mode
        if not use_llm or model is None:
            result = _mock_audit(article, simulation)
            logger.info(
                "geo_eval_audit article_id=%s engine=mock passed=%s score=%s",
                article.id,
                result["audit_passed"],
                result["audit_score"],
            )
            return result

        user = (
            f"用户问题：{simulation.get('query') or article.title}\n"
            f"模拟 RAG 回答：{simulation.get('simulated_answer', '')[:500]}\n"
            f"检索得分：{simulation.get('retrieval_score')} 模拟得分：{simulation.get('simulation_score')}\n"
            f"文章标题：{article.title}\n"
            f"文章摘要：{(article.meta_description or article.excerpt or '')[:300]}\n"
            f"文章正文（节选）：{(article.content or '')[:2000]}"
        )
        try:
            parsed = await chat_json(model, system=AUDIT_SYSTEM, user=user)
        except Exception:
            logger.exception("geo_eval_audit_llm_failed article_id=%s", article.id)
            result = _mock_audit(article, simulation)
            result["engine"] = "mock_fallback"
            return result

        checks_raw = parsed.get("checks") if isinstance(parsed.get("checks"), dict) else {}
        checks = {
            "answers_query": bool(checks_raw.get("answers_query")),
            "structured": bool(checks_raw.get("structured")),
            "grounded": bool(checks_raw.get("grounded")),
            "entity_clear": bool(checks_raw.get("entity_clear")),
        }
        failures = [str(f) for f in (parsed.get("failures") or []) if f][:5]
        audit_score = float(parsed.get("audit_score") or 0.5)
        audit_passed = bool(parsed.get("audit_passed"))

        min_score = self.settings.geo_eval_audit_pass_score
        if audit_score < min_score:
            audit_passed = False
            failures.append(f"audit_score_below_threshold:{audit_score:.2f}")

        result = {
            "audit_passed": audit_passed,
            "audit_score": round(audit_score, 4),
            "checks": checks,
            "failures": failures,
            "engine": "llm",
            "model": {"model_id": model.model_id, "model_name": model.name, "ai_model_id": model.id},
        }
        logger.info(
            "geo_eval_audit article_id=%s engine=llm passed=%s score=%s",
            article.id,
            audit_passed,
            audit_score,
        )
        return result
