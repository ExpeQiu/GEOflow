"""GEO 评估引擎 — RAG 模拟 + LLM 审计 + Wiki 合规门禁。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.services.geoeval.answer_audit import AnswerAuditService
from app.services.geoeval.eval_context import resolve_eval_model, resolve_kb_id
from app.services.geoeval.simulation_rag import SimulationRagService
from app.services.geoeval.wiki_compliance import WikiGeoComplianceChecker

settings = get_settings()


class ArticleEvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wiki_checker = WikiGeoComplianceChecker()
        self.simulation = SimulationRagService(db)
        self.audit = AnswerAuditService(db)

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

        failures: list[str] = []
        metrics: dict = {}

        kb_id = await resolve_kb_id(self.db, article)
        model = await resolve_eval_model(self.db, article)

        sim = await self.simulation.simulate(article, kb_id=kb_id, model=model)
        audit = await self.audit.audit(article, sim, model=model)

        metrics["simulation"] = sim
        metrics["audit"] = audit
        metrics["simulation_score"] = sim["simulation_score"]
        metrics["audit_passed"] = audit["audit_passed"]
        metrics["audit_score"] = audit["audit_score"]
        metrics["kb_id"] = kb_id

        if sim["simulation_score"] < settings.geo_eval_simulation_pass_score:
            failures.append(f"simulation_score_low:{sim['simulation_score']:.2f}")
        if not audit["audit_passed"]:
            failures.extend(audit.get("failures") or ["audit_failed"])

        if article.content_format == "wiki_mdx" and settings.geo_eval_wiki_gate_enabled:
            wiki_result = self.wiki_checker.check(article.content, article.wiki_meta or {})
            metrics["wiki_compliance"] = wiki_result
            if not wiki_result.get("passed"):
                failures.extend(wiki_result.get("failures", []))

        failure_reason = "; ".join(dict.fromkeys(failures))[:500] if failures else None

        if failure_reason:
            evaluation.status = "failed"
            evaluation.failure_reason = failure_reason
            article.eval_status = "failed"
        else:
            evaluation.status = "passed"
            article.eval_status = "passed"

        evaluation.metrics = metrics
        article.eval_meta = metrics
        evaluation.updated_at = datetime.now(UTC).replace(tzinfo=None)
        return evaluation
