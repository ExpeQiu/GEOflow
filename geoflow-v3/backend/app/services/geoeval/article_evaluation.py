"""GEO 评估引擎 — RAG 模拟 + LLM 审计 + Wiki 合规（默认软门禁：评分/建议）。"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config
from app.services.geoeval.answer_audit import AnswerAuditService
from app.services.geoeval.eval_context import resolve_eval_model, resolve_kb_id
from app.services.geoeval.eval_recommendations import build_recommendations
from app.services.geoeval.simulation_rag import SimulationRagService
from app.services.geoeval.wiki_compliance import WikiGeoComplianceChecker

logger = logging.getLogger(__name__)


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

        gate = await get_geo_eval_gate_config(self.db)
        sim_pass = float(gate["simulation_pass_score"])
        audit_pass = float(gate["audit_pass_score"])
        wiki_enabled = bool(gate["wiki_checks_enabled"])
        hard_gate = bool(gate["hard_gate"])

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
        metrics["pass_thresholds"] = {
            "simulation_pass_score": sim_pass,
            "audit_pass_score": audit_pass,
        }

        if sim["simulation_score"] < sim_pass:
            failures.append(f"simulation_score_low:{sim['simulation_score']:.2f}")
        if not audit["audit_passed"]:
            failures.extend(audit.get("failures") or ["audit_failed"])
        elif float(audit.get("audit_score") or 0) < audit_pass:
            failures.append(f"audit_score_low:{float(audit.get('audit_score') or 0):.2f}")

        if article.content_format == "wiki_mdx" and wiki_enabled:
            wiki_result = self.wiki_checker.check(article.content, article.wiki_meta or {})
            metrics["wiki_compliance"] = wiki_result
            if not wiki_result.get("passed"):
                failures.extend(wiki_result.get("failures", []))

        recommendations = build_recommendations(
            issues=failures,
            simulation_score=sim.get("simulation_score"),
            audit_score=audit.get("audit_score"),
            pass_score=sim_pass,
        )
        meets_thresholds = len(failures) == 0
        issue_text = "; ".join(dict.fromkeys(failures))[:500] if failures else None

        metrics["gate_mode"] = "hard" if hard_gate else "soft"
        metrics["meets_thresholds"] = meets_thresholds
        metrics["advisory_issues"] = list(dict.fromkeys(failures))
        metrics["recommendations"] = recommendations

        if hard_gate and not meets_thresholds:
            evaluation.status = "failed"
            evaluation.failure_reason = issue_text
            article.eval_status = "failed"
        elif not meets_thresholds:
            # 软门禁：可发布，状态 advisory 供 UI 展示建议
            evaluation.status = "advisory"
            evaluation.failure_reason = issue_text
            article.eval_status = "advisory"
        else:
            evaluation.status = "passed"
            evaluation.failure_reason = None
            article.eval_status = "passed"

        evaluation.metrics = metrics
        article.eval_meta = metrics
        evaluation.updated_at = datetime.now(UTC).replace(tzinfo=None)

        logger.info(
            "geo_eval_completed article_id=%s status=%s gate_mode=%s score=%s issues=%s recs=%s sim_pass=%s",
            article_id,
            evaluation.status,
            metrics["gate_mode"],
            sim.get("simulation_score"),
            len(failures),
            len(recommendations),
            sim_pass,
        )
        return evaluation
