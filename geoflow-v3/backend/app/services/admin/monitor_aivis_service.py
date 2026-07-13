"""AIVIS Monitor CRUD — 场景、模板、竞品、报告、趋势。"""

import json
import logging
import re

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.entity_classifier import infer_entity_type

logger = logging.getLogger(__name__)


class MonitorSceneBody(BaseModel):
    persona: str = ""
    scene_name: str = Field(min_length=1, max_length=200)
    intent: str = ""
    weight_pct: float = Field(default=0, ge=0, le=100)
    industry: str = ""
    insight_template_id: int | None = None
    status: str = Field(default="active", pattern="^(active|paused)$")


class QueryTemplateBody(BaseModel):
    template_type: str = Field(default="brand", pattern="^(brand|product|competitor)$")
    category: str = ""
    pattern: str = Field(min_length=1)
    scene_id: int | None = None
    default_priority: int = Field(default=50, ge=0, le=100)
    status: str = Field(default="active", pattern="^(active|paused)$")


class CompetitorBody(BaseModel):
    brand_name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list)
    is_self: bool = False
    status: str = Field(default="active", pattern="^(active|paused)$")
    entity_type: str = Field(default="brand", pattern="^(brand|product)$")


async def _competitors_has_entity_type(db: AsyncSession) -> bool:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'geo_monitor_competitors' AND column_name = 'entity_type'
                    """
                )
            )
        ).first()
        return bool(row)
    except Exception:
        return False


class MonitorQuestionExtendedBody(BaseModel):
    question_text: str = Field(min_length=1)
    priority: int = Field(default=50, ge=0, le=100)
    status: str = Field(default="active", pattern="^(active|paused)$")
    scene_id: int | None = None
    template_id: int | None = None
    query_type: str = Field(default="brand", pattern="^(brand|product|competitor)$")
    competitor_brands: list[str] = Field(default_factory=list)


async def list_monitor_scenes(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, persona, scene_name, intent, weight_pct, industry,
                       gap_rate, gap_priority, insight_template_id, status, last_gap_at
                FROM geo_monitor_scenes ORDER BY weight_pct DESC, id DESC
                """
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "persona": r[1] or "",
                "scene_name": r[2],
                "intent": r[3] or "",
                "weight_pct": float(r[4] or 0),
                "industry": r[5] or "",
                "gap_rate": float(r[6] or 0),
                "gap_priority": r[7] or "covered",
                "insight_template_id": r[8],
                "status": r[9],
                "last_gap_at": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]
    }


async def create_monitor_scene(db: AsyncSession, body: MonitorSceneBody) -> dict:
    if not await _table_exists(db, "geo_monitor_scenes"):
        raise HTTPException(status_code=503, detail="aivis_not_migrated")
    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_scenes
                    (persona, scene_name, intent, weight_pct, industry, insight_template_id, status)
                VALUES (:p, :sn, :i, :w, :ind, :it, :s) RETURNING id
                """
            ),
            {
                "p": body.persona.strip(),
                "sn": body.scene_name.strip(),
                "i": body.intent.strip(),
                "w": body.weight_pct,
                "ind": body.industry.strip(),
                "it": body.insight_template_id,
                "s": body.status,
            },
        )
    ).first()
    return {"item": {"id": int(row[0]), "scene_name": body.scene_name}}


async def list_query_templates(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_monitor_query_templates"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, template_type, category, pattern, scene_id, default_priority, status
                FROM geo_monitor_query_templates ORDER BY id DESC
                """
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "template_type": r[1],
                "category": r[2] or "",
                "pattern": r[3],
                "scene_id": r[4],
                "default_priority": int(r[5] or 50),
                "status": r[6],
            }
            for r in rows
        ]
    }


async def create_query_template(db: AsyncSession, body: QueryTemplateBody) -> dict:
    if not await _table_exists(db, "geo_monitor_query_templates"):
        raise HTTPException(status_code=503, detail="aivis_not_migrated")
    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_query_templates
                    (template_type, category, pattern, scene_id, default_priority, status)
                VALUES (:tt, :cat, :pat, :sid, :dp, :s) RETURNING id
                """
            ),
            {
                "tt": body.template_type,
                "cat": body.category.strip(),
                "pat": body.pattern.strip(),
                "sid": body.scene_id,
                "dp": body.default_priority,
                "s": body.status,
            },
        )
    ).first()
    return {"item": {"id": int(row[0]), "pattern": body.pattern}}


async def generate_questions_from_template(db: AsyncSession, template_id: int, limit: int = 20) -> dict:
    if not await _table_exists(db, "geo_monitor_query_templates"):
        raise HTTPException(status_code=503, detail="aivis_not_migrated")
    tpl = (
        await db.execute(
            text(
                """
                SELECT pattern, template_type, scene_id, default_priority
                FROM geo_monitor_query_templates WHERE id = :id
                """
            ),
            {"id": template_id},
        )
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="template_not_found")

    pattern, qtype, scene_id, priority = tpl[0], tpl[1], tpl[2], int(tpl[3] or 50)
    placeholders = re.findall(r"\{(\w+)\}", pattern)
    samples: list[str] = []

    if placeholders:
        defaults = {"brand": "品牌", "product": "产品", "competitor": "竞品", "scene": "场景"}
        for i in range(min(limit, 10)):
            q = pattern
            for ph in placeholders:
                q = q.replace("{" + ph + "}", defaults.get(ph, f"样例{i+1}"))
            samples.append(q)
    else:
        samples = [pattern]

    created = 0
    for qtext in samples[:limit]:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_questions
                    (question_text, priority, status, scene_id, template_id, query_type, competitor_brands)
                VALUES (:q, :p, 'active', :sid, :tid, :qt, '[]'::json)
                """
            ),
            {"q": qtext, "p": priority, "sid": scene_id, "tid": template_id, "qt": qtype},
        )
        created += 1

    logger.info("template_questions_generated template_id=%s count=%s", template_id, created)
    return {"created": created, "template_id": template_id}


async def list_competitors(db: AsyncSession, entity_type: str = "brand") -> dict:
    if not await _table_exists(db, "geo_monitor_competitors"):
        return {"items": []}
    has_type = await _competitors_has_entity_type(db)
    if entity_type == "product" and not has_type:
        return {"items": []}
    type_filter = "AND entity_type = :etype" if has_type else ""
    rows = (
        await db.execute(
            text(
                f"""
                SELECT id, brand_name, aliases, is_self, status
                FROM geo_monitor_competitors
                WHERE 1=1 {type_filter}
                ORDER BY is_self DESC, id
                """
            ),
            {"etype": entity_type} if has_type else {},
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "brand_name": r[1],
                "aliases": r[2] or [],
                "is_self": bool(r[3]),
                "status": r[4],
            }
            for r in rows
            if infer_entity_type(str(r[1])) == entity_type
        ]
    }


async def create_competitor(db: AsyncSession, body: CompetitorBody) -> dict:
    if not await _table_exists(db, "geo_monitor_competitors"):
        raise HTTPException(status_code=503, detail="aivis_not_migrated")
    entity_type = body.entity_type or "brand"
    if entity_type == "brand" and infer_entity_type(body.brand_name) == "product":
        raise HTTPException(status_code=400, detail="请输入品牌名称（如吉利汽车），而非智驾产品/系统")
    if entity_type == "product" and infer_entity_type(body.brand_name) == "brand":
        raise HTTPException(status_code=400, detail="请输入智驾产品/系统名称（如华为 ADS、千里浩瀚G-ASD），而非品牌名")
    has_type = await _competitors_has_entity_type(db)
    if has_type:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_competitors (brand_name, aliases, is_self, status, entity_type)
                    VALUES (:n, CAST(:a AS JSON), :self, :s, :etype) RETURNING id
                    """
                ),
                {
                    "n": body.brand_name.strip(),
                    "a": json.dumps(body.aliases, ensure_ascii=False),
                    "self": body.is_self,
                    "s": body.status,
                    "etype": body.entity_type,
                },
            )
        ).first()
    else:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_competitors (brand_name, aliases, is_self, status)
                    VALUES (:n, CAST(:a AS JSON), :self, :s) RETURNING id
                    """
                ),
                {"n": body.brand_name.strip(), "a": json.dumps(body.aliases, ensure_ascii=False), "self": body.is_self, "s": body.status},
            )
        ).first()
    logger.info("competitor_created name=%s entity_type=%s is_self=%s", body.brand_name, body.entity_type, body.is_self)
    return {"item": {"id": int(row[0]), "brand_name": body.brand_name}}


async def list_products(db: AsyncSession) -> dict:
    return await list_competitors(db, entity_type="product")


async def create_product(db: AsyncSession, body: CompetitorBody) -> dict:
    return await create_competitor(db, body.model_copy(update={"entity_type": "product"}))


async def list_monitor_snapshots(db: AsyncSession, days: int = 30) -> dict:
    if not await _table_exists(db, "geo_monitor_snapshots"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT snapshot_date, visibility_pct, weighted_rank_score, sentiment_score, mention_rate
                FROM geo_monitor_snapshots
                ORDER BY snapshot_date DESC
                LIMIT :lim
                """
            ),
            {"lim": days},
        )
    ).all()
    items = [
        {
            "date": str(r[0]),
            "visibility_pct": float(r[1] or 0),
            "weighted_rank_score": float(r[2] or 0) if r[2] is not None else None,
            "sentiment_score": float(r[3]) if r[3] is not None else None,
            "mention_rate": float(r[4] or 0),
        }
        for r in rows
    ]
    return {"items": list(reversed(items))}


async def list_visibility_reports(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_visibility_reports"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, period_start, period_end, status, html_path, created_at
                FROM geo_visibility_reports ORDER BY id DESC LIMIT 30
                """
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "title": r[1],
                "period_start": str(r[2]) if r[2] else None,
                "period_end": str(r[3]) if r[3] else None,
                "status": r[4],
                "html_path": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


async def list_monitor_insights(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_monitor_insights"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, insight_type, title, body, payload, created_at
                FROM geo_monitor_insights WHERE status = 'active'
                ORDER BY id DESC LIMIT 20
                """
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "insight_type": r[1],
                "title": r[2],
                "body": r[3],
                "payload": r[4] or {},
                "created_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]
    }
