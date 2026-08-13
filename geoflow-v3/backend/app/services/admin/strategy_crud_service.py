"""策略写操作 — Insight Templates / Monitor / WebIntel / Simulator。"""

import csv
import io
import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.geoeval import InsightTemplate
from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


class InsightTemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_url: str = ""


class MonitorQuestionBody(BaseModel):
    question_text: str = Field(min_length=1)
    priority: int = Field(default=50, ge=0, le=100)
    status: str = Field(default="active", pattern="^(active|paused)$")
    scene_id: int | None = None
    template_id: int | None = None
    query_type: str = Field(default="brand", pattern="^(brand|product|competitor)$")
    competitor_brands: list[str] = Field(default_factory=list)


class WebSourceBody(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    label: str = ""


class BatchReevalBody(BaseModel):
    article_ids: list[int] = Field(min_length=1, max_length=50)


class MonitorQuestionBulkBody(BaseModel):
    items: list[MonitorQuestionBody] | None = Field(default=None, max_length=200)
    csv_text: str | None = Field(default=None, max_length=200_000)
    skip_duplicates: bool = True


def _question_row_mapping(has_extended: bool) -> tuple[str, tuple[str, ...]]:
    if has_extended:
        return (
            "id, question_text, priority, status, last_scan_at, scene_id, template_id, query_type, competitor_brands",
            (
                "id",
                "question_text",
                "priority",
                "status",
                "last_scan_at",
                "scene_id",
                "template_id",
                "query_type",
                "competitor_brands",
            ),
        )
    return (
        "id, question_text, priority, status, last_scan_at",
        ("id", "question_text", "priority", "status", "last_scan_at"),
    )


def _normalize_question_key(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _parse_csv_monitor_questions(csv_text: str) -> list[MonitorQuestionBody]:
    """解析 CSV：question_text,priority,query_type,status,scene_id,competitor_brands"""
    raw = csv_text.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="csv_empty")

    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="csv_missing_header")

    header_map = {h.strip().lower(): h for h in reader.fieldnames if h}
    text_key = header_map.get("question_text") or header_map.get("问题") or header_map.get("question")
    if not text_key:
        raise HTTPException(status_code=400, detail="csv_missing_question_text_column")

    items: list[MonitorQuestionBody] = []
    for line_no, row in enumerate(reader, start=2):
        qtext = (row.get(text_key) or "").strip()
        if not qtext:
            continue

        priority_key = header_map.get("priority") or header_map.get("优先级")
        qtype_key = header_map.get("query_type") or header_map.get("类型")
        status_key = header_map.get("status") or header_map.get("状态")
        scene_key = header_map.get("scene_id") or header_map.get("场景id")
        comp_key = header_map.get("competitor_brands") or header_map.get("竞品")

        priority_raw = (row.get(priority_key) or "50").strip() if priority_key else "50"
        try:
            priority = max(0, min(100, int(priority_raw)))
        except ValueError:
            priority = 50

        query_type = (row.get(qtype_key) or "brand").strip() if qtype_key else "brand"
        if query_type not in ("brand", "product", "competitor"):
            query_type = "brand"

        status = (row.get(status_key) or "active").strip() if status_key else "active"
        if status not in ("active", "paused"):
            status = "active"

        scene_id = None
        if scene_key and (row.get(scene_key) or "").strip():
            try:
                scene_id = int(str(row.get(scene_key)).strip())
            except ValueError:
                logger.warning("csv_invalid_scene_id line=%s value=%s", line_no, row.get(scene_key))

        competitors: list[str] = []
        if comp_key and (row.get(comp_key) or "").strip():
            raw_comp = str(row.get(comp_key)).strip()
            sep = "|" if "|" in raw_comp else ","
            competitors = [c.strip() for c in raw_comp.split(sep) if c.strip()]

        items.append(
            MonitorQuestionBody(
                question_text=qtext,
                priority=priority,
                status=status,
                query_type=query_type,
                scene_id=scene_id,
                competitor_brands=competitors,
            )
        )

    if not items:
        raise HTTPException(status_code=400, detail="csv_no_valid_rows")
    if len(items) > 200:
        raise HTTPException(status_code=400, detail="csv_too_many_rows")
    return items


async def list_monitor_questions(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    query_type: str | None = None,
    status: str | None = None,
    scene_id: int | None = None,
    search: str | None = None,
) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "stats": {"total": 0, "brand": 0, "product": 0, "competitor": 0, "active": 0},
        }

    has_extended = await _table_exists(db, "geo_monitor_scenes")
    cols_sql, col_names = _question_row_mapping(has_extended)

    where = ["1=1"]
    params: dict = {}
    if query_type and has_extended:
        where.append("COALESCE(query_type, 'brand') = :qt")
        params["qt"] = query_type
    if status:
        where.append("status = :st")
        params["st"] = status
    if scene_id is not None and has_extended:
        where.append("scene_id = :sid")
        params["sid"] = scene_id
    if search:
        where.append("question_text ILIKE :q")
        params["q"] = f"%{search.strip()}%"

    where_sql = " AND ".join(where)
    total = int(await db.scalar(text(f"SELECT COUNT(*) FROM geo_monitor_questions WHERE {where_sql}"), params) or 0)

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    params["lim"] = page_size
    params["off"] = offset

    rows = (
        await db.execute(
            text(
                f"""
                SELECT {cols_sql}
                FROM geo_monitor_questions
                WHERE {where_sql}
                ORDER BY priority DESC, id DESC
                LIMIT :lim OFFSET :off
                """
            ),
            params,
        )
    ).all()
    items = [dict(zip(col_names, row)) for row in rows]

    if has_extended:
        stats_row = (
            await db.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN COALESCE(query_type, 'brand') = 'brand' THEN 1 ELSE 0 END) AS brand,
                        SUM(CASE WHEN query_type = 'product' THEN 1 ELSE 0 END) AS product,
                        SUM(CASE WHEN query_type = 'competitor' THEN 1 ELSE 0 END) AS competitor,
                        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active
                    FROM geo_monitor_questions
                    """
                )
            )
        ).first()
    else:
        stats_row = (
            await db.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) AS brand,
                        0 AS product,
                        0 AS competitor,
                        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active
                    FROM geo_monitor_questions
                    """
                )
            )
        ).first()
    stats = {
        "total": int(stats_row[0] or 0) if stats_row else 0,
        "brand": int(stats_row[1] or 0) if stats_row else 0,
        "product": int(stats_row[2] or 0) if stats_row else 0,
        "competitor": int(stats_row[3] or 0) if stats_row else 0,
        "active": int(stats_row[4] or 0) if stats_row else 0,
    }

    logger.info(
        "monitor_questions_listed page=%s page_size=%s total=%s query_type=%s status=%s scene_id=%s",
        page,
        page_size,
        total,
        query_type,
        status,
        scene_id,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "stats": stats}


async def bulk_import_monitor_questions(db: AsyncSession, body: MonitorQuestionBulkBody) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")

    items: list[MonitorQuestionBody] = []
    if body.csv_text:
        items = _parse_csv_monitor_questions(body.csv_text)
    elif body.items:
        items = body.items
    else:
        raise HTTPException(status_code=400, detail="bulk_import_empty")

    existing_rows = (await db.execute(text("SELECT question_text FROM geo_monitor_questions"))).all()
    existing_keys = {_normalize_question_key(str(r[0])) for r in existing_rows if r[0]}

    created = 0
    skipped = 0
    errors: list[dict] = []

    for idx, item in enumerate(items):
        key = _normalize_question_key(item.question_text)
        if body.skip_duplicates and key in existing_keys:
            skipped += 1
            continue
        try:
            result = await create_monitor_question(db, item)
            created += 1
            existing_keys.add(key)
            logger.debug("bulk_question_created id=%s", result.get("item", {}).get("id"))
        except HTTPException as exc:
            errors.append({"index": idx, "question_text": item.question_text, "detail": exc.detail})
        except Exception as exc:
            errors.append({"index": idx, "question_text": item.question_text, "detail": str(exc)})

    logger.info("monitor_questions_bulk_import created=%s skipped=%s errors=%s", created, skipped, len(errors))
    return {"created": created, "skipped": skipped, "errors": errors, "total_input": len(items)}


async def seed_default_brand_questions(db: AsyncSession) -> dict:
    """一键补品牌类探针（冷启动）。"""
    from app.services.admin.monitor_settings_service import get_monitor_settings

    settings = await get_monitor_settings(db)
    brand = (settings.get("brand_name") or "品牌").strip()
    lines = [
        "question_text,priority,query_type,status",
        f"{brand}怎么样,95,brand,active",
        f"{brand}口碑如何,92,brand,active",
        f"{brand}技术实力怎么样,90,brand,active",
        f"{brand}和竞品相比有什么优势,88,competitor,active",
        f"买{brand}的车靠谱吗,85,brand,active",
    ]
    return await bulk_import_monitor_questions(
        db,
        MonitorQuestionBulkBody(csv_text="\n".join(lines), skip_duplicates=True),
    )


async def list_insight_templates_crud(db: AsyncSession) -> dict:
    rows = (await db.execute(select(InsightTemplate).order_by(InsightTemplate.id.desc()))).scalars().all()
    return {
        "items": [
            {"id": t.id, "name": t.name, "source_url": t.source_url or "", "eeat_score": float(t.eeat_score or 0)}
            for t in rows
        ]
    }


async def create_insight_template(db: AsyncSession, body: InsightTemplateBody) -> dict:
    row = InsightTemplate(name=body.name.strip(), source_url=body.source_url.strip() or None)
    db.add(row)
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def update_insight_template(db: AsyncSession, template_id: int, body: InsightTemplateBody) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    row.name = body.name.strip()
    row.source_url = body.source_url.strip() or None
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def delete_insight_template(db: AsyncSession, template_id: int) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    await db.delete(row)
    return {"deleted": True}


async def remine_insight_template(db: AsyncSession, template_id: int) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.remine_insight_template", args=[template_id])
    logger.info("insight_template_remine_queued id=%s", template_id)
    return {"queued": True, "template_id": template_id}


async def create_monitor_question(db: AsyncSession, body: MonitorQuestionBody) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    import json

    if await _table_exists(db, "geo_monitor_scenes"):
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_questions
                        (question_text, priority, status, scene_id, template_id, query_type, competitor_brands)
                    VALUES (:q, :p, :s, :sid, :tid, :qt, CAST(:cb AS JSON))
                    RETURNING id
                    """
                ),
                {
                    "q": body.question_text.strip(),
                    "p": body.priority,
                    "s": body.status,
                    "sid": body.scene_id,
                    "tid": body.template_id,
                    "qt": body.query_type,
                    "cb": json.dumps(body.competitor_brands, ensure_ascii=False),
                },
            )
        ).first()
    else:
        row = (
            await db.execute(
                text(
                    "INSERT INTO geo_monitor_questions (question_text, priority, status) VALUES (:q, :p, :s) RETURNING id"
                ),
                {"q": body.question_text.strip(), "p": body.priority, "s": body.status},
            )
        ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "question_text": body.question_text.strip()}}


async def update_monitor_question(db: AsyncSession, question_id: int, body: MonitorQuestionBody) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    import json

    if await _table_exists(db, "geo_monitor_scenes"):
        result = await db.execute(
            text(
                """
                UPDATE geo_monitor_questions
                SET question_text=:q, priority=:p, status=:s, scene_id=:sid, template_id=:tid,
                    query_type=:qt, competitor_brands=CAST(:cb AS JSON), updated_at=CURRENT_TIMESTAMP
                WHERE id=:id
                """
            ),
            {
                "q": body.question_text.strip(),
                "p": body.priority,
                "s": body.status,
                "sid": body.scene_id,
                "tid": body.template_id,
                "qt": body.query_type,
                "cb": json.dumps(body.competitor_brands, ensure_ascii=False),
                "id": question_id,
            },
        )
    else:
        result = await db.execute(
            text(
                "UPDATE geo_monitor_questions SET question_text=:q, priority=:p, status=:s, updated_at=CURRENT_TIMESTAMP WHERE id=:id"
            ),
            {"q": body.question_text.strip(), "p": body.priority, "s": body.status, "id": question_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="question_not_found")
    return {"item": {"id": question_id}}


async def delete_monitor_question(db: AsyncSession, question_id: int) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    await db.execute(text("DELETE FROM geo_monitor_questions WHERE id=:id"), {"id": question_id})
    return {"deleted": True}


async def create_web_source(db: AsyncSession, body: WebSourceBody) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    row = (
        await db.execute(
            text("INSERT INTO geo_web_sources (url, label) VALUES (:u, :l) RETURNING id"),
            {"u": body.url.strip(), "l": body.label.strip()},
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "url": body.url.strip()}}


async def delete_web_source(db: AsyncSession, source_id: int) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    await db.execute(text("DELETE FROM geo_web_sources WHERE id=:id"), {"id": source_id})
    return {"deleted": True}


async def refresh_web_source(db: AsyncSession, source_id: int) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.fetch_web_source", args=[source_id])
    return {"queued": True, "source_id": source_id}


async def batch_reevaluate(db: AsyncSession, body: BatchReevalBody) -> dict:
    from app.workers.celery_app import celery_app

    queued = 0
    for aid in body.article_ids:
        article = await db.get(Article, aid)
        if article and not article.deleted_at:
            celery_app.send_task("app.workers.tasks.evaluate_article", args=[aid])
            queued += 1
    logger.info("batch_reevaluate_queued count=%s", queued)
    return {"queued": queued}


async def apply_recommendations(db: AsyncSession, article_id: int) -> dict:
    from app.models.geoeval import ArticleEvaluation

    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    ev = (
        await db.execute(
            select(ArticleEvaluation)
            .where(ArticleEvaluation.article_id == article_id)
            .order_by(ArticleEvaluation.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    note = "recommendations_applied"
    changed: list[str] = []
    eval_meta = dict(article.eval_meta or {})
    if ev:
        metrics = ev.metrics if isinstance(ev.metrics, dict) else {}
        recs = metrics.get("recommendations") or metrics.get("suggestions") or []
        reason = ev.failure_reason or ""
        if isinstance(recs, list) and recs:
            eval_meta["applied_recommendations"] = recs
            for item in recs:
                if isinstance(item, dict) and item.get("field") == "title" and item.get("value"):
                    article.title = str(item["value"])[:200]
                    changed.append("title")
                    break
            note = str(recs[0])[:500]
        elif reason:
            eval_meta["applied_recommendations"] = reason
            note = reason[:500]
        score = metrics.get("simulation_score")
        if score is not None:
            eval_meta["last_simulation_score"] = float(score)
            changed.append("simulation_score")
    article.eval_meta = eval_meta
    await db.flush()
    logger.info("apply_recommendations article_id=%s changed=%s", article_id, changed)
    return {"applied": True, "article_id": article_id, "note": note, "changed_fields": changed}
