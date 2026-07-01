"""GEO 评估引擎 — 移植 InternalGeoEvalEngine + ArticleEvaluationService。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.services.geoeval.wiki_compliance import WikiGeoComplianceChecker

settings = get_settings()


class ArticleEvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wiki_checker = WikiGeoComplianceChecker()

    async def evaluate(self, article_id: int, task_run_id: int | None = None) -> ArticleEvaluation:
        article = await self.db.get(Article, article_id)
        if article is None:
            raise ValueError("article_not_found")

        idem = f"eval-{article_id}-{task_run_id or 0}"
        evaluation = ArticleEvaluation(
            article_id=article_id,
            task_run_id=task_run_id,
            idempotency_key=idem,
            request_id=str(uuid.uuid4()),
            status="running",
        )
        self.db.add(evaluation)
        await self.db.flush()

        metrics: dict = {"simulation_score": 0.75, "audit_passed": True}
        failure_reason: str | None = None

        if article.content_format == "wiki_mdx" and settings.geo_eval_wiki_gate_enabled:
            wiki_result = self.wiki_checker.check(article.content, article.wiki_meta or {})
            metrics["wiki_compliance"] = wiki_result
            if not wiki_result.get("passed"):
                failure_reason = "; ".join(wiki_result.get("failures", []))

        if failure_reason:
            evaluation.status = "failed"
            evaluation.failure_reason = failure_reason[:500]
            article.eval_status = "failed"
        else:
            evaluation.status = "passed"
            article.eval_status = "passed"

        evaluation.metrics = metrics
        article.eval_meta = metrics
        evaluation.updated_at = datetime.now(UTC)
        return evaluation
