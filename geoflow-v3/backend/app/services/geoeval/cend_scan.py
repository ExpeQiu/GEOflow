"""C 端金标扫描编排 — 独立于 daily api 扫描，避免污染主轨 KPI。"""

from __future__ import annotations

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.monitor_probe import load_brand_keywords, load_scan_limit, _persist_probe
from app.services.geoeval.platform_connectors.cend.connector import probe_cend_platform
from app.services.geoeval.platform_connectors.cend.registry import list_cend_platforms

logger = logging.getLogger("geoeval.cend_scan")

DEFAULT_CEND_LIMIT = 5
MAX_CEND_LIMIT = 20


class CendScanOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _platforms(self, platforms: list[str] | None) -> list[str]:
        allowed = set(list_cend_platforms())
        if platforms:
            return [p for p in platforms if p in allowed]
        raw = os.getenv("CEND_SCAN_PLATFORMS", "yuanbao").strip()
        if raw:
            return [p.strip() for p in raw.split(",") if p.strip() in allowed]
        return ["yuanbao"]

    async def _load_questions(self, *, limit: int, min_priority: int) -> list[tuple]:
        if not await _table_exists(self.db, "geo_monitor_questions"):
            return []
        rows = (
            await self.db.execute(
                text(
                    """
                    SELECT id, question_text, priority, competitor_brands
                    FROM geo_monitor_questions
                    WHERE status = 'active' AND priority >= :floor
                    ORDER BY priority DESC, id ASC
                    LIMIT :lim
                    """
                ),
                {"floor": min_priority, "lim": limit},
            )
        ).all()
        logger.info("cend_questions_loaded count=%s limit=%s floor=%s", len(rows), limit, min_priority)
        return list(rows)

    async def run_scan(
        self,
        *,
        platforms: list[str] | None = None,
        limit: int | None = None,
        min_priority: int = 80,
        write_gold: bool = True,
    ) -> dict:
        plat_list = await self._platforms(platforms)
        lim = max(1, min(MAX_CEND_LIMIT, int(limit or DEFAULT_CEND_LIMIT)))
        # 不超过 monitor_scan_limit
        try:
            lim = min(lim, await load_scan_limit(self.db))
        except Exception:
            pass

        questions = await self._load_questions(limit=lim, min_priority=min_priority)
        brands = await load_brand_keywords(self.db)

        run_id = None
        if await _table_exists(self.db, "geo_monitor_runs"):
            row = (
                await self.db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_runs (status, platform, question_count, probe_count, started_at)
                        VALUES ('running', :platform, :qc, 0, CURRENT_TIMESTAMP)
                        RETURNING id
                        """
                    ),
                    {
                        "platform": f"cend:{','.join(plat_list)}"[:200],
                        "qc": len(questions),
                    },
                )
            ).first()
            run_id = int(row[0]) if row else None

        outcomes_n = 0
        engine_counts: dict[str, int] = {}
        gold_written = 0

        for q in questions:
            qid, qtext, priority = int(q[0]), str(q[1]), int(q[2] or 0)
            comp_raw = q[3] if len(q) > 3 else None
            comps: list[str] | None = None
            if isinstance(comp_raw, list):
                comps = [str(x) for x in comp_raw]
            elif isinstance(comp_raw, str) and comp_raw.strip():
                import json

                try:
                    parsed = json.loads(comp_raw)
                    if isinstance(parsed, list):
                        comps = [str(x) for x in parsed]
                except json.JSONDecodeError:
                    comps = [p.strip() for p in comp_raw.split(",") if p.strip()]

            for platform in plat_list:
                outcome = await probe_cend_platform(
                    question_text=qtext,
                    platform=platform,
                    brand_list=brands,
                    competitor_brands=comps,
                    question_id=qid,
                )
                engine_counts[outcome.engine] = engine_counts.get(outcome.engine, 0) + 1
                if run_id:
                    probe_id = await _persist_probe(self.db, run_id=run_id, outcome=outcome)
                else:
                    probe_id = None
                outcomes_n += 1

                if write_gold and outcome.engine == "cend_browser" and await _table_exists(
                    self.db, "geo_probe_gold_labels"
                ):
                    await self._upsert_gold(qid, platform, outcome, probe_id)
                    gold_written += 1

            await self.db.execute(
                text(
                    """
                    UPDATE geo_monitor_questions
                    SET last_scan_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": qid},
            )

        if run_id:
            await self.db.execute(
                text(
                    """
                    UPDATE geo_monitor_runs
                    SET status='completed', probe_count=:pc, completed_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                    """
                ),
                {"pc": outcomes_n, "id": run_id},
            )

        try:
            from app.services.admin.distribution_citation_service import refresh_distribution_citation_cache

            citation_cache = await refresh_distribution_citation_cache(self.db)
        except Exception:
            logger.warning("cend_citation_refresh_failed", exc_info=True)
            citation_cache = {}

        skipped = engine_counts.get("skipped", 0)
        if outcomes_n > 0 and skipped / outcomes_n >= 0.5 and await _table_exists(self.db, "geo_admin_alerts"):
            import json

            await self.db.execute(
                text(
                    """
                    INSERT INTO geo_admin_alerts (alert_type, message, payload_json)
                    VALUES ('cend_profile_or_dom', :m, CAST(:p AS JSON))
                    """
                ),
                {
                    "m": f"C端扫描 skipped 占比过高（{skipped}/{outcomes_n}），请检查登录 Profile 或 DOM 选择器",
                    "p": json.dumps(
                        {"skipped": skipped, "total": outcomes_n, "platforms": plat_list},
                        ensure_ascii=False,
                    ),
                },
            )
            logger.warning("cend_high_skip_alert skipped=%s total=%s", skipped, outcomes_n)

        logger.info(
            "cend_scan_completed run_id=%s probes=%s platforms=%s engines=%s gold=%s",
            run_id,
            outcomes_n,
            plat_list,
            engine_counts,
            gold_written,
        )
        return {
            "status": "completed",
            "scan_type": "cend",
            "run_id": run_id,
            "probes": outcomes_n,
            "question_count": len(questions),
            "platforms": plat_list,
            "engine_mix": [{"engine": k, "count": v} for k, v in engine_counts.items()],
            "gold_written": gold_written,
            "metric_kind": "cend_sample",
            "citation_cache": {
                "indexed": citation_cache.get("indexed_count", 0),
                "not_indexed": citation_cache.get("not_indexed_count", 0),
            },
        }

    async def _upsert_gold(self, question_id: int, platform: str, outcome, probe_id: int | None) -> None:
        import json

        urls_json = json.dumps(outcome.citation_urls or outcome.urls or [], ensure_ascii=False)
        base = {
            "qid": question_id,
            "plat": platform,
            "mentioned": bool(outcome.mentioned),
            "rank": outcome.brand_rank,
            "snippet": (outcome.snippet or "")[:2000],
            "urls": urls_json,
            "opid": probe_id,
            "notes": "cend_scan",
        }
        try:
            await self.db.execute(
                text(
                    """
                    INSERT INTO geo_probe_gold_labels
                        (question_id, platform, source, mentioned, brand_rank, snippet, cited_urls,
                         open_api_probe_id, notes, thinking_text, keywords, rank_blocks, decision_table,
                         source_hosts, capture_artifact, cend_meta, captured_at)
                    VALUES
                        (:qid, :plat, 'browser_sandbox', :mentioned, :rank, :snippet,
                         CAST(:urls AS JSONB), :opid, :notes, :thinking,
                         CAST(:keywords AS JSONB), CAST(:blocks AS JSONB), CAST(:table AS JSONB),
                         CAST(:hosts AS JSONB), :artifact, CAST(:meta AS JSONB), CURRENT_TIMESTAMP)
                    """
                ),
                {
                    **base,
                    "thinking": (outcome.thinking_text or "")[:8000] or None,
                    "keywords": json.dumps(outcome.keywords or [], ensure_ascii=False),
                    "blocks": json.dumps(outcome.rank_blocks or [], ensure_ascii=False),
                    "table": json.dumps(outcome.decision_table or [], ensure_ascii=False),
                    "hosts": json.dumps(outcome.source_hosts or [], ensure_ascii=False),
                    "artifact": outcome.capture_artifact,
                    "meta": json.dumps(outcome.cend_meta or {}, ensure_ascii=False),
                },
            )
        except Exception:
            await self.db.execute(
                text(
                    """
                    INSERT INTO geo_probe_gold_labels
                        (question_id, platform, source, mentioned, brand_rank, snippet, cited_urls,
                         open_api_probe_id, notes, captured_at)
                    VALUES
                        (:qid, :plat, 'browser_sandbox', :mentioned, :rank, :snippet,
                         CAST(:urls AS JSONB), :opid, :notes, CURRENT_TIMESTAMP)
                    """
                ),
                base,
            )
