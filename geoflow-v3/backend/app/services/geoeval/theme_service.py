"""Theme 主题包服务：草稿 → 确认 → 生产 → 门禁聚合 → 分发状态。"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.theme import DEFAULT_PACK_SPEC, GeoTheme
from app.services.geoflow.wiki_types import ascii_slug
from app.services.admin.materials_libraries_service import (
    LibraryBody,
    TitleBody,
    create_title,
    create_title_library,
)
from app.services.admin.production_service import _table_exists
from app.services.admin.task_form_service import AdminTaskCreateBody, create_admin_task
from app.services.geoeval.scene_gap_analyzer import compute_scene_gap

logger = logging.getLogger(__name__)

DOMAINS = ("adas", "battery", "edrive", "cockpit", "safety")


def _slugify(text_in: str) -> str:
    return ascii_slug(text_in, fallback="theme")


def _iso_ts(t: GeoTheme, attr: str) -> str | None:
    """读取时间戳；flush 后 onupdate 列可能已 expire，勿触发同步 lazy load。"""
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(t)
    if attr in state.unloaded:
        return None
    val = state.dict.get(attr)
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else None


def _theme_dict(t: GeoTheme) -> dict[str, Any]:
    return {
        "id": t.id,
        "slug": t.slug,
        "title": t.title,
        "scene_id": t.scene_id,
        "status": t.status,
        "domain": t.domain,
        "gate_mode": t.gate_mode or "soft",
        "target_queries": t.target_queries or [],
        "pack_spec": t.pack_spec or [],
        "knowledge_base_id": t.knowledge_base_id,
        "insight_template_id": t.insight_template_id,
        "prompt_id": t.prompt_id,
        "ai_model_id": t.ai_model_id,
        "title_library_id": t.title_library_id,
        "task_id": t.task_id,
        "remediation_id": t.remediation_id,
        "gate_summary": t.gate_summary or {},
        "geoweb_hub_slug": t.geoweb_hub_slug,
        "meta": t.meta or {},
        "created_at": _iso_ts(t, "created_at"),
        "updated_at": _iso_ts(t, "updated_at"),
    }


def remaining_pack_runs(created_count: int | None, article_limit: int | None) -> int:
    """启生产应入队的剩余篇数（复合包一次出齐）。"""
    limit = max(int(article_limit or 0), 0)
    created = max(int(created_count or 0), 0)
    return max(0, limit - created)


def pack_type_for_title(pack: list | None, title: str, created_count: int | None, fallback: str) -> str:
    """按标题匹配 pack_spec.type，避免 Mock/并行入队错配页型。"""
    want = (title or "").strip()
    for item in pack or []:
        if str(item.get("title") or "").strip() == want and item.get("type"):
            return str(item["type"])
    idx = max(0, int(created_count or 0))
    if pack and idx < len(pack) and pack[idx].get("type"):
        return str(pack[idx]["type"])
    return fallback


def _build_default_pack(title: str, queries: list[str]) -> list[dict]:
    pack: list[dict] = []
    for i, spec in enumerate(DEFAULT_PACK_SPEC):
        item = dict(spec)
        q = queries[i] if i < len(queries) else (queries[0] if queries else title)
        item["title"] = f"{title} · {spec['type']}" if spec["type"] != "topic" else title
        item["query"] = q
        pack.append(item)
    return pack


class ThemeCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    slug: str | None = None
    scene_id: int | None = None
    domain: str | None = None
    gate_mode: str = "soft"
    target_queries: list[str] = Field(default_factory=list)
    pack_spec: list[dict] | None = None
    knowledge_base_id: int | None = None
    insight_template_id: int | None = None
    prompt_id: int | None = None
    ai_model_id: int | None = None


class ThemePatchBody(BaseModel):
    title: str | None = None
    domain: str | None = None
    gate_mode: str | None = None
    target_queries: list[str] | None = None
    pack_spec: list[dict] | None = None
    knowledge_base_id: int | None = None
    insight_template_id: int | None = None
    prompt_id: int | None = None
    ai_model_id: int | None = None
    status: str | None = None


async def _load_gap_defaults(db: AsyncSession) -> dict:
    defaults = {
        "title_library_id": None,
        "prompt_id": None,
        "ai_model_id": None,
        "knowledge_base_id": None,
    }
    if not await _table_exists(db, "site_settings"):
        return defaults
    key_map = {
        "gap_task_title_library_id": "title_library_id",
        "gap_task_prompt_id": "prompt_id",
        "gap_task_ai_model_id": "ai_model_id",
        "default_knowledge_base_id": "knowledge_base_id",
    }
    rows = (
        await db.execute(
            text(
                """
                SELECT setting_key, setting_value FROM site_settings
                WHERE setting_key IN (
                    'gap_task_title_library_id', 'gap_task_prompt_id',
                    'gap_task_ai_model_id', 'default_knowledge_base_id'
                )
                """
            )
        )
    ).all()
    for key, value in rows:
        field = key_map.get(str(key))
        if field and value:
            try:
                defaults[field] = int(value)
            except (TypeError, ValueError):
                pass
    return defaults


async def _fallback_ids(db: AsyncSession) -> tuple[int, int]:
    prompt = (
        await db.execute(text("SELECT id FROM prompts ORDER BY id LIMIT 1"))
    ).scalar_one_or_none()
    model = (
        await db.execute(text("SELECT id FROM ai_models WHERE status = 'active' ORDER BY id LIMIT 1"))
    ).scalar_one_or_none()
    if not prompt or not model:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "theme_defaults_missing",
                "message": "缺少 prompt 或 ai_model，请先到 内容生产 → AI 配置",
                "hint": "/production/ai_config",
            },
        )
    return int(prompt), int(model)


async def resolve_default_geoweb_channel_ids(db: AsyncSession) -> list[int]:
    if not await _table_exists(db, "distribution_channels"):
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT id FROM distribution_channels
                WHERE channel_type = 'geoweb' AND status = 'active'
                ORDER BY id ASC
                """
            )
        )
    ).all()
    return [int(r[0]) for r in rows]


async def list_themes(db: AsyncSession, *, status: str | None = None, limit: int = 100) -> dict:
    if not await _table_exists(db, "geo_themes"):
        return {"items": [], "status": "table_missing"}
    q = select(GeoTheme).order_by(GeoTheme.id.desc()).limit(min(limit, 500))
    if status:
        q = q.where(GeoTheme.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_theme_dict(t) for t in rows], "total": len(rows)}


async def get_theme(db: AsyncSession, theme_id: int) -> dict:
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    articles = []
    if await _table_exists(db, "articles"):
        art_rows = (
            await db.execute(
                text(
                    """
                    SELECT id, title, slug, status, eval_status, content_format, wiki_meta
                    FROM articles WHERE theme_id = :tid ORDER BY id ASC
                    """
                ),
                {"tid": theme_id},
            )
        ).all()
        for r in art_rows:
            wiki_meta = r[6] if isinstance(r[6], dict) else {}
            articles.append(
                {
                    "id": int(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "status": r[3],
                    "eval_status": r[4],
                    "content_format": r[5],
                    "wiki_page_type": (wiki_meta or {}).get("type") or (wiki_meta or {}).get("wiki_page_type"),
                }
            )
    data = _theme_dict(theme)
    data["articles"] = articles
    return data


async def create_theme(db: AsyncSession, body: ThemeCreateBody) -> dict:
    if not await _table_exists(db, "geo_themes"):
        raise HTTPException(status_code=503, detail="geo_themes_not_migrated")
    title = body.title.strip()
    slug = _slugify(body.slug or title)
    # ensure unique
    base = slug
    n = 1
    while await db.scalar(select(GeoTheme.id).where(GeoTheme.slug == slug)):
        slug = f"{base}-{n}"
        n += 1
    domain = body.domain if body.domain in DOMAINS else body.domain
    queries = [q.strip() for q in body.target_queries if q and q.strip()]
    pack = body.pack_spec if body.pack_spec else _build_default_pack(title, queries)
    theme = GeoTheme(
        slug=slug,
        title=title,
        scene_id=body.scene_id,
        status="draft",
        domain=domain,
        gate_mode=body.gate_mode if body.gate_mode in ("soft", "hard") else "soft",
        target_queries=queries,
        pack_spec=pack,
        knowledge_base_id=body.knowledge_base_id,
        insight_template_id=body.insight_template_id,
        prompt_id=body.prompt_id,
        ai_model_id=body.ai_model_id,
        meta={},
    )
    db.add(theme)
    await db.flush()
    logger.info(
        "theme_created theme_id=%s slug=%s scene_id=%s status=draft",
        theme.id,
        theme.slug,
        theme.scene_id,
    )
    return {"theme": _theme_dict(theme)}


async def create_theme_from_scene(db: AsyncSession, scene_id: int) -> dict:
    """场景缺口 → 主题挖掘 → 草稿 Theme（人工确认后才生产）。"""
    from app.services.geoeval.theme_mining_service import mine_theme_from_gap

    gap = await compute_scene_gap(db, scene_id)
    if gap.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="scene_not_found")
    if gap.get("status") == "skipped":
        raise HTTPException(status_code=503, detail=gap.get("reason") or "scenes_unavailable")

    scene_row = (
        await db.execute(
            text(
                """
                SELECT scene_name, intent, insight_template_id, gap_rate, persona
                FROM geo_monitor_scenes WHERE id = :id
                """
            ),
            {"id": scene_id},
        )
    ).first()
    if not scene_row:
        raise HTTPException(status_code=404, detail="scene_not_found")

    defaults = await _load_gap_defaults(db)
    mined = await mine_theme_from_gap(
        db,
        scene_id=scene_id,
        gap=gap,
        persona=scene_row[4],
        scene_name=str(scene_row[0] or ""),
        intent=scene_row[1],
    )
    mining = mined["mining"]
    title = str(mined.get("campaign_title") or f"{scene_row[0]}：补齐 AI 决策链内容")[:300]
    queries = list(mining.get("longtail_queries") or [])
    if not queries:
        queries = [title]

    body = ThemeCreateBody(
        title=title,
        scene_id=scene_id,
        target_queries=queries,
        knowledge_base_id=defaults.get("knowledge_base_id"),
        insight_template_id=int(scene_row[2]) if scene_row[2] else None,
        prompt_id=defaults.get("prompt_id"),
        ai_model_id=defaults.get("ai_model_id"),
        gate_mode="hard",
    )
    result = await create_theme(db, body)
    theme = result["theme"]
    row = await db.get(GeoTheme, theme["id"])
    if row:
        row.meta = {
            "source": "monitor_gap",
            "gap_rate": float(scene_row[3] or gap.get("gap_rate") or 0),
            "gap_priority": gap.get("gap_priority"),
            "persona": scene_row[4],
            "mining": mining,
            "probe_evidence": mining.get("probe_evidence") or [],
            "candidates": mined.get("candidates") or [],
        }
        row.gate_mode = "hard"
        await db.flush()
        theme = _theme_dict(row)

    logger.info(
        "theme_draft_from_scene theme_id=%s scene_id=%s gap_rate=%s longtails=%s evidence=%s",
        theme["id"],
        scene_id,
        gap.get("gap_rate"),
        len(queries),
        len(mining.get("probe_evidence") or []),
    )
    return {
        "theme": theme,
        "gap": {
            "gap_rate": gap.get("gap_rate"),
            "gap_priority": gap.get("gap_priority"),
            "unsupported_sample": gap.get("unsupported_sample"),
        },
        "candidates": mined.get("candidates") or [],
        "mining": mining,
    }


async def create_theme_from_question(
    db: AsyncSession,
    question_id: int,
    flags: list[str] | None = None,
) -> dict:
    """交叉判定缺口 → 同一场景 Theme 草稿，并把该题写入 target_queries。"""
    row = (
        await db.execute(
            text(
                """
                SELECT id, scene_id, question_text
                FROM geo_monitor_questions WHERE id = :id
                """
            ),
            {"id": question_id},
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="question_not_found")
    scene_id = row[1]
    if not scene_id:
        raise HTTPException(status_code=422, detail="question_has_no_scene")
    result = await create_theme_from_scene(db, int(scene_id))
    theme_row = await db.get(GeoTheme, result["theme"]["id"])
    qtext = str(row[2] or "").strip()
    if theme_row:
        meta = dict(theme_row.meta or {})
        meta["source"] = "cross_track"
        meta["source_question_id"] = question_id
        meta["cross_flags"] = [str(f) for f in (flags or []) if f]
        theme_row.meta = meta
        queries = [str(q) for q in (theme_row.target_queries or []) if q]
        if qtext and qtext not in queries:
            theme_row.target_queries = [qtext] + queries
        await db.flush()
        result["theme"] = _theme_dict(theme_row)
    logger.info(
        "theme_draft_from_cross_track theme_id=%s question_id=%s scene_id=%s flags=%s",
        result["theme"]["id"],
        question_id,
        scene_id,
        flags or [],
    )
    return result


async def spawn_theme_candidate(db: AsyncSession, theme_id: int, candidate_index: int = 0) -> dict:
    """从已有 Theme 的 mining.candidates 另存草稿。"""
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    meta = theme.meta if isinstance(theme.meta, dict) else {}
    candidates = meta.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=422, detail="no_candidates")
    if candidate_index < 0 or candidate_index >= len(candidates):
        raise HTTPException(status_code=422, detail="candidate_index_invalid")
    cand = candidates[candidate_index]
    title = str(cand.get("title") or f"{theme.title} · 候选{candidate_index + 1}")[:300]
    queries = list(cand.get("target_queries") or theme.target_queries or [])
    mining = dict(meta.get("mining") or {})
    mining["spawned_from_theme_id"] = theme.id
    mining["candidate_index"] = candidate_index

    body = ThemeCreateBody(
        title=title,
        scene_id=theme.scene_id,
        domain=theme.domain,
        gate_mode=theme.gate_mode or "hard",
        target_queries=queries,
        pack_spec=theme.pack_spec,
        knowledge_base_id=theme.knowledge_base_id,
        insight_template_id=theme.insight_template_id,
        prompt_id=theme.prompt_id,
        ai_model_id=theme.ai_model_id,
    )
    result = await create_theme(db, body)
    new_theme = await db.get(GeoTheme, result["theme"]["id"])
    if new_theme:
        new_theme.meta = {
            "source": "mining_candidate",
            "parent_theme_id": theme.id,
            "gap_rate": meta.get("gap_rate"),
            "gap_priority": meta.get("gap_priority"),
            "persona": meta.get("persona"),
            "mining": mining,
            "probe_evidence": meta.get("probe_evidence") or mining.get("probe_evidence") or [],
            "candidates": [],
        }
        new_theme.gate_mode = theme.gate_mode or "hard"
        await db.flush()
        result = {"theme": _theme_dict(new_theme)}
    logger.info(
        "theme_candidate_spawned parent_id=%s new_id=%s index=%s",
        theme_id,
        result["theme"]["id"],
        candidate_index,
    )
    return result


async def patch_theme(db: AsyncSession, theme_id: int, body: ThemePatchBody) -> dict:
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    data = body.model_dump(exclude_unset=True)
    for key, val in data.items():
        if key == "gate_mode" and val not in ("soft", "hard"):
            continue
        if key == "status" and val not in (
            "draft",
            "confirmed",
            "producing",
            "gate_passed",
            "distributing",
            "published",
            "measuring",
            "completed",
        ):
            continue
        setattr(theme, key, val)
    await db.flush()
    logger.info("theme_patched theme_id=%s keys=%s", theme_id, list(data.keys()))
    return {"theme": _theme_dict(theme)}


async def confirm_theme(db: AsyncSession, theme_id: int) -> dict:
    """确认规格：写标题库、建 Task（绑 GEOweb 渠道）、建 remediation。"""
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    if theme.status not in ("draft", "confirmed"):
        raise HTTPException(status_code=422, detail=f"theme_status_invalid:{theme.status}")

    channel_ids = await resolve_default_geoweb_channel_ids(db)
    # 幂等：已确认且已有任务则直接返回，避免重复建标题库/Task
    if theme.status == "confirmed" and theme.task_id:
        await db.refresh(theme)
        return {
            "theme": _theme_dict(theme),
            "task_id": int(theme.task_id),
            "distribution_channel_ids": channel_ids,
            "remediation": {"remediation_id": theme.remediation_id} if theme.remediation_id else None,
            "idempotent": True,
        }

    if not channel_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "geoweb_channel_missing",
                "message": "缺少活跃 GEOweb 分发渠道，请先到 运营与分发 → 分发管理 配置",
                "hint": "/operations/distribution",
            },
        )

    defaults = await _load_gap_defaults(db)
    try:
        prompt_fb, model_fb = await _fallback_ids(db)
    except HTTPException:
        raise
    prompt_id = theme.prompt_id or defaults.get("prompt_id") or prompt_fb
    model_id = theme.ai_model_id or defaults.get("ai_model_id") or model_fb
    kb_id = theme.knowledge_base_id or defaults.get("knowledge_base_id")

    pack = theme.pack_spec or _build_default_pack(theme.title, theme.target_queries or [])
    # ensure titles filled
    for item in pack:
        if not item.get("title"):
            item["title"] = f"{theme.title} · {item.get('type', 'page')}"
    theme.pack_spec = pack

    # dedicated title library from pack + queries
    lib = await create_title_library(
        db, LibraryBody(name=f"[Theme] {theme.title}"[:100], description=f"theme:{theme.id}")
    )
    lib_id = int(lib["item"]["id"])
    for item in pack:
        await create_title(
            db,
            lib_id,
            TitleBody(title=str(item["title"])[:500], keyword=str(item.get("query") or "")[:200]),
        )
    # also seed remaining target queries as extra titles if any
    existing_titles = {str(i.get("title")) for i in pack}
    for q in theme.target_queries or []:
        if q and q not in existing_titles:
            await create_title(db, lib_id, TitleBody(title=q[:500], keyword=q[:200]))

    required_count = sum(1 for i in pack if i.get("required", True))
    article_limit = max(required_count, len([i for i in pack if i.get("required", True)]))

    task_body = AdminTaskCreateBody(
        task_name=f"[Theme] {theme.title}"[:200],
        title_library_id=lib_id,
        prompt_id=int(prompt_id),
        ai_model_id=int(model_id),
        knowledge_base_id=int(kb_id) if kb_id else None,
        insight_template_id=theme.insight_template_id,
        content_format="wiki_mdx",
        wiki_page_type="concept",
        publish_scope="distribution_only",
        distribution_channel_ids=channel_ids,
        article_limit=article_limit,
        draft_limit=article_limit,
        need_review=False,
        is_loop=False,
    )
    task_result = await create_admin_task(db, task_body)
    task_id = int(task_result["task"]["id"])

    remediation = None
    if theme.scene_id:
        from app.services.geoeval.remediation_service import create_remediation_for_gap

        gap_rate = float((theme.meta or {}).get("gap_rate") or 0)
        remediation = await create_remediation_for_gap(
            db,
            scene_id=int(theme.scene_id),
            task_id=task_id,
            gap_rate=gap_rate,
            gap_priority=(theme.meta or {}).get("gap_priority"),
            theme_id=theme.id,
        )

    theme.title_library_id = lib_id
    theme.prompt_id = int(prompt_id)
    theme.ai_model_id = int(model_id)
    theme.knowledge_base_id = int(kb_id) if kb_id else None
    theme.task_id = task_id
    theme.remediation_id = (remediation or {}).get("remediation_id")
    theme.status = "confirmed"
    theme.geoweb_hub_slug = theme.slug
    await db.flush()

    # stamp task_runs meta if any
    if await _table_exists(db, "task_runs"):
        meta = {
            "source": "theme",
            "theme_id": theme.id,
            "scene_id": theme.scene_id,
            "remediation_id": theme.remediation_id,
        }
        run_id = (
            await db.execute(
                text("SELECT id FROM task_runs WHERE task_id = :tid ORDER BY id DESC LIMIT 1"),
                {"tid": task_id},
            )
        ).scalar_one_or_none()
        if run_id:
            await db.execute(
                text("UPDATE task_runs SET meta = :meta WHERE id = :id"),
                {"meta": json.dumps(meta, ensure_ascii=False), "id": int(run_id)},
            )

    # onupdate=func.now() 会在 flush 后 expire updated_at；先 refresh 再序列化
    await db.refresh(theme)
    logger.info(
        "theme_confirmed theme_id=%s task_id=%s title_library_id=%s channels=%s remediation_id=%s",
        theme.id,
        task_id,
        lib_id,
        channel_ids,
        theme.remediation_id,
    )
    return {
        "theme": _theme_dict(theme),
        "task_id": task_id,
        "distribution_channel_ids": channel_ids,
        "remediation": remediation,
    }


async def start_produce(db: AsyncSession, theme_id: int) -> dict:
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    if theme.status == "draft":
        raise HTTPException(status_code=422, detail="theme_not_confirmed")
    if not theme.task_id:
        raise HTTPException(status_code=422, detail="theme_task_missing")

    from app.models.task import Task
    from app.services.geoflow.task_lifecycle import TaskLifecycleService

    task = await db.get(Task, int(theme.task_id))
    if task is None:
        raise HTTPException(status_code=422, detail="theme_task_missing")

    remaining = remaining_pack_runs(task.created_count, task.article_limit)
    svc = TaskLifecycleService(db)
    run_ids: list[int] = []
    for _ in range(remaining):
        run = await svc.enqueue(theme.task_id)
        run_ids.append(int(run.id))
    if remaining:
        theme.status = "producing"
        await db.flush()
    logger.info(
        "theme_produce_started theme_id=%s task_id=%s status=%s remaining=%s run_ids=%s",
        theme.id,
        theme.task_id,
        theme.status,
        remaining,
        run_ids,
    )
    return {
        "theme": _theme_dict(theme),
        "enqueued": remaining > 0,
        "remaining": remaining,
        "run_ids": run_ids,
    }


async def refresh_theme_gate_summary(db: AsyncSession, theme_id: int) -> dict:
    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        return {"status": "not_found"}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, eval_status, status, wiki_meta
                FROM articles WHERE theme_id = :tid AND deleted_at IS NULL
                """
            ),
            {"tid": theme_id},
        )
    ).all()
    by_status: dict[str, int] = {}
    articles = []
    for r in rows:
        es = str(r[1] or "skipped")
        by_status[es] = by_status.get(es, 0) + 1
        wiki_meta = r[3] if isinstance(r[3], dict) else {}
        articles.append(
            {
                "id": int(r[0]),
                "eval_status": es,
                "status": r[2],
                "type": (wiki_meta or {}).get("type"),
            }
        )

    pack = theme.pack_spec or []
    required_types = {str(i.get("type")) for i in pack if i.get("required", True)}
    present_passed = set()
    for a in articles:
        if a["eval_status"] in ("passed", "advisory", "skipped") and a.get("type"):
            if theme.gate_mode == "hard" and a["eval_status"] != "passed":
                continue
            present_passed.add(a["type"])

    required_ok = required_types.issubset(present_passed) if required_types else (
        len(articles) > 0 and all(a["eval_status"] in ("passed", "advisory", "skipped") for a in articles)
        if theme.gate_mode == "soft"
        else all(a["eval_status"] == "passed" for a in articles)
    )
    # soft: advisory allowed for required
    if theme.gate_mode == "soft" and required_types:
        soft_ok = set()
        for a in articles:
            if a["eval_status"] in ("passed", "advisory", "skipped") and a.get("type"):
                soft_ok.add(a["type"])
        required_ok = required_types.issubset(soft_ok)

    summary = {
        "article_count": len(articles),
        "by_eval_status": by_status,
        "required_types": sorted(required_types),
        "passed_types": sorted(present_passed),
        "pack_gate_ok": bool(required_ok) if articles else False,
        "gate_mode": theme.gate_mode or "soft",
    }
    theme.gate_summary = summary
    if summary["pack_gate_ok"] and theme.status in ("producing", "confirmed"):
        theme.status = "gate_passed"
    elif articles and theme.gate_mode == "hard" and not summary["pack_gate_ok"]:
        # stay producing / allow rework — do not auto-revert to draft here
        pass
    await db.flush()
    logger.info(
        "theme_gate_refreshed theme_id=%s pack_gate_ok=%s by_status=%s",
        theme_id,
        summary["pack_gate_ok"],
        by_status,
    )
    return {"theme_id": theme_id, "gate_summary": summary, "status": theme.status}


async def theme_allows_distribute(db: AsyncSession, theme_id: int) -> tuple[bool, str]:
    summary = await refresh_theme_gate_summary(db, theme_id)
    gs = summary.get("gate_summary") or {}
    if gs.get("pack_gate_ok"):
        return True, "ok"
    mode = gs.get("gate_mode") or "soft"
    if mode == "soft" and (gs.get("article_count") or 0) > 0:
        # soft still allows if any article evaluated (advisory ok) — pack_gate_ok already encodes this
        return False, "theme_pack_gate_pending"
    return False, "theme_pack_gate_blocked"


async def mark_theme_distributing(db: AsyncSession, theme_id: int) -> None:
    theme = await db.get(GeoTheme, theme_id)
    if theme and theme.status in ("gate_passed", "producing", "confirmed"):
        theme.status = "distributing"
        await db.flush()


async def mark_theme_published(db: AsyncSession, theme_id: int, *, hub_slug: str | None = None) -> None:
    theme = await db.get(GeoTheme, theme_id)
    if not theme:
        return
    if hub_slug:
        theme.geoweb_hub_slug = hub_slug
    summary = await refresh_theme_gate_summary(db, theme_id)
    gs = summary.get("gate_summary") or {}
    if not gs.get("pack_gate_ok"):
        logger.info(
            "theme_publish_deferred theme_id=%s pack_gate_ok=false article_count=%s",
            theme_id,
            gs.get("article_count"),
        )
        return
    theme = await db.get(GeoTheme, theme_id)
    if not theme:
        return
    if hub_slug:
        theme.geoweb_hub_slug = hub_slug
    theme.status = "published"
    if theme.remediation_id:
        theme.status = "measuring"
    await db.flush()
    logger.info("theme_published theme_id=%s hub=%s status=%s", theme_id, theme.geoweb_hub_slug, theme.status)


async def theme_funnel_stats(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_themes"):
        return {"by_status": {}, "total": 0, "blockers": []}
    rows = (await db.execute(text("SELECT status, COUNT(*) FROM geo_themes GROUP BY status"))).all()
    by_status = {str(r[0]): int(r[1]) for r in rows}
    blockers = []
    channels = await resolve_default_geoweb_channel_ids(db)
    if not channels:
        blockers.append({"code": "geoweb_channel_missing", "hint": "/operations/distribution"})
    failed = (
        await db.execute(
            text(
                """
                SELECT COUNT(*) FROM geo_themes
                WHERE status = 'producing'
                  AND COALESCE((gate_summary->>'pack_gate_ok')::text, 'false') = 'false'
                """
            )
        )
    ).scalar_one_or_none()
    if failed and int(failed) > 0:
        blockers.append({"code": "gate_failed_themes", "count": int(failed), "hint": "/production/themes"})
    return {
        "by_status": by_status,
        "total": sum(by_status.values()),
        "blockers": blockers,
        "draft": by_status.get("draft", 0),
        "producing": by_status.get("producing", 0) + by_status.get("confirmed", 0),
        "published": by_status.get("published", 0) + by_status.get("measuring", 0) + by_status.get("completed", 0),
        "measuring": by_status.get("measuring", 0),
        "gate_passed": by_status.get("gate_passed", 0),
    }


async def analytics_by_theme(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_themes"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT t.id, t.title, t.status, t.gate_mode,
                       (SELECT COUNT(*) FROM articles a WHERE a.theme_id = t.id AND a.deleted_at IS NULL) AS art_cnt,
                       (SELECT COUNT(*) FROM articles a WHERE a.theme_id = t.id AND a.eval_status = 'passed' AND a.deleted_at IS NULL) AS passed_cnt,
                       (SELECT COUNT(*) FROM article_distributions d
                          JOIN articles a ON a.id = d.article_id
                         WHERE a.theme_id = t.id AND d.status = 'published') AS dist_ok,
                       (SELECT COUNT(*) FROM article_distributions d
                          JOIN articles a ON a.id = d.article_id
                         WHERE a.theme_id = t.id) AS dist_total
                FROM geo_themes t
                ORDER BY t.id DESC
                LIMIT 100
                """
            )
        )
    ).all()
    items = []
    for r in rows:
        art = int(r[4] or 0)
        passed = int(r[5] or 0)
        dist_ok = int(r[6] or 0)
        dist_total = int(r[7] or 0)
        items.append(
            {
                "theme_id": int(r[0]),
                "title": r[1],
                "status": r[2],
                "gate_mode": r[3],
                "article_count": art,
                "gate_pass_rate_pct": round(passed / art * 100, 1) if art else 0.0,
                "distribution_success_rate_pct": round(dist_ok / dist_total * 100, 1) if dist_total else 0.0,
            }
        )
    return {"items": items}
