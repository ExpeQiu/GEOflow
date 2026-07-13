"""任务执行前解析 L2 生产素材 — 标题/分类/作者/关键词/图片/模型/洞察。"""

import json
import logging
import random
import re
from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geoeval import InsightTemplate
from app.models.material import AiModel, Author, Category
from app.models.task import Task
from app.models.tech_ip import TechIpAsset
from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


class TaskMaterialContext:
    """单次 TaskRun 解析后的生产上下文。"""

    def __init__(self) -> None:
        self.title: str = ""
        self.title_id: int | None = None
        self.title_keyword: str = ""
        self.category_id: int | None = None
        self.author_id: int | None = None
        self.keywords: str = ""
        self.meta_description: str = ""
        self.images: list[dict[str, Any]] = []
        self.model: dict[str, Any] = {}
        self.ai_model_id: int | None = None
        self.style_guide: str = ""
        self.tech_ip: dict[str, Any] | None = None


async def resolve_task_materials(db: AsyncSession, task: Task, run_id: int) -> TaskMaterialContext:
    ctx = TaskMaterialContext()
    await _pick_title(db, task, ctx)
    ctx.category_id = await _resolve_category_id(db, task, run_id)
    ctx.author_id = await _resolve_author_id(db, task)
    ctx.model, ctx.ai_model_id = await _resolve_ai_model(db, task)
    ctx.style_guide = await _load_style_guide(db, task)
    ctx.tech_ip = await _load_tech_ip(db, task)
    if ctx.tech_ip:
        ctx.style_guide = (ctx.style_guide + "\n\n" + ctx.tech_ip.get("prompt_block", "")).strip()
    logger.info(
        "task_materials_resolved task_id=%s run_id=%s title_id=%s category_id=%s author_id=%s model_id=%s",
        task.id,
        run_id,
        ctx.title_id,
        ctx.category_id,
        ctx.author_id,
        ctx.ai_model_id,
    )
    return ctx


def resolve_workflow_type(task: Task) -> str:
    mode = (task.content_pipeline_mode or "legacy").strip().lower()
    if mode in {"pipeline", "auto"}:
        return "content_pipeline"
    return "content"


def normalize_evidence(chunks: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            continue
        cid = chunk.get("chunk_id") or chunk.get("id") or index
        normalized.append({**chunk, "id": cid, "chunk_id": cid})
    return normalized


def append_images_to_content(content: str, images: list[dict]) -> str:
    if not images:
        return content
    lines = ["\n\n---\n\n## 配图\n"]
    for image in images:
        path = str(image.get("file_path") or image.get("original_name") or "")
        name = str(image.get("original_name") or "image")
        if path:
            lines.append(f"![{name}]({path})")
    return content.rstrip() + "\n".join(lines) + "\n"


def build_meta_description(content: str, limit: int = 160) -> str:
    plain = re.sub(r"[#*`>\[\]()]", " ", content)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= limit:
        return plain
    return plain[: limit - 1].rstrip() + "…"


async def finalize_article_fields(
    db: AsyncSession,
    task: Task,
    ctx: TaskMaterialContext,
    content: str,
) -> dict[str, Any]:
    images = await _pick_images(db, task)
    ctx.images = images
    enriched_content = append_images_to_content(content, images)

    keywords = ctx.title_keyword
    if task.auto_keywords:
        keywords = await _sample_keywords(db, task, ctx.title_keyword, enriched_content)

    meta_description = ""
    if task.auto_description:
        meta_description = build_meta_description(enriched_content)

    return {
        "content": enriched_content,
        "keywords": keywords,
        "original_keyword": ctx.title_keyword,
        "meta_description": meta_description,
    }


async def _pick_title(db: AsyncSession, task: Task, ctx: TaskMaterialContext) -> None:
    if not await _table_exists(db, "titles"):
        ctx.title = task.name
        return

    row = (
        await db.execute(
            text(
                """
                SELECT id, title, keyword
                FROM titles
                WHERE library_id = :lid
                ORDER BY used_count ASC, id ASC
                LIMIT 1
                """
            ),
            {"lid": task.title_library_id},
        )
    ).first()

    if not row:
        logger.warning("title_library_empty task_id=%s library_id=%s", task.id, task.title_library_id)
        ctx.title = task.name
        return

    ctx.title_id = int(row[0])
    ctx.title = str(row[1])
    ctx.title_keyword = str(row[2] or "")
    await db.execute(
        text("UPDATE titles SET used_count = used_count + 1 WHERE id = :id"),
        {"id": ctx.title_id},
    )


async def _resolve_category_id(db: AsyncSession, task: Task, run_id: int) -> int:
    mode = (task.category_mode or "smart").strip().lower()
    if mode == "fixed" and task.fixed_category_id:
        return int(task.fixed_category_id)

    categories = (await db.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
    if not categories:
        return 1

    if mode == "random":
        return random.choice(categories).id

    # smart：按 task_id + run_id 稳定选取，避免完全随机
    index = (int(task.id) + int(run_id)) % len(categories)
    return categories[index].id


async def _resolve_author_id(db: AsyncSession, task: Task) -> int:
    if task.author_id and task.author_id > 0:
        return int(task.author_id)

    authors = (await db.execute(select(Author).order_by(Author.id))).scalars().all()
    if not authors:
        return 1
    return random.choice(authors).id


async def _resolve_ai_model(db: AsyncSession, task: Task) -> tuple[dict, int | None]:
    if task.model_selection_mode == "smart_failover":
        models = (
            await db.execute(
                select(AiModel)
                .where(
                    AiModel.status == "active",
                    or_(AiModel.model_type == "chat", AiModel.model_type == "", AiModel.model_type.is_(None)),
                )
                .order_by(AiModel.failover_priority, AiModel.id)
            )
        ).scalars().all()
        ordered: list[AiModel] = []
        primary = await db.get(AiModel, task.ai_model_id)
        if primary and primary.status == "active":
            ordered.append(primary)
        for model in models:
            if model.id not in {m.id for m in ordered}:
                ordered.append(model)
        if not ordered:
            raise RuntimeError("no_active_chat_model")
        chosen = ordered[0]
    else:
        chosen = await db.get(AiModel, task.ai_model_id)
        if chosen is None or chosen.status != "active":
            raise RuntimeError("ai_model_unavailable")

    model_dict = {
        "id": chosen.id,
        "name": chosen.name,
        "model_id": chosen.model_id,
        "provider_url": chosen.api_url,
        "api_key": chosen.api_key,
    }
    return model_dict, chosen.id


async def _load_style_guide(db: AsyncSession, task: Task) -> str:
    if not task.insight_template_id:
        return ""
    template = await db.get(InsightTemplate, task.insight_template_id)
    if template is None:
        return ""
    if isinstance(template.style_guide, dict) and template.style_guide:
        return json.dumps(template.style_guide, ensure_ascii=False, indent=2)
    if template.source_url:
        return f"参考来源：{template.source_url}"
    return ""


async def _load_tech_ip(db: AsyncSession, task: Task) -> dict[str, Any] | None:
    if not task.tech_ip_asset_id:
        return None
    asset = await db.get(TechIpAsset, task.tech_ip_asset_id)
    if asset is None:
        return None
    prompt_block = (
        f"技术 IP：{asset.name}（{asset.ip_id}）\n"
        f"Wiki 类型：{asset.wiki_type}\n"
        f"描述：{asset.description or '无'}"
    )
    return {
        "ip_id": asset.ip_id,
        "name": asset.name,
        "wiki_type": asset.wiki_type,
        "description": asset.description,
        "prompt_block": prompt_block,
    }


async def _pick_images(db: AsyncSession, task: Task) -> list[dict[str, Any]]:
    if not task.image_library_id or not task.image_count or task.image_count <= 0:
        return []
    if not await _table_exists(db, "images"):
        return []

    rows = (
        await db.execute(
            text(
                """
                SELECT id, original_name, file_path, mime_type
                FROM images
                WHERE library_id = :lid
                ORDER BY RANDOM()
                LIMIT :lim
                """
            ),
            {"lid": task.image_library_id, "lim": int(task.image_count)},
        )
    ).all()
    return [
        {"id": int(r[0]), "original_name": r[1], "file_path": r[2], "mime_type": r[3] or ""}
        for r in rows
    ]


async def _sample_keywords(db: AsyncSession, task: Task, title_keyword: str, content: str) -> str:
    keywords: list[str] = []
    if title_keyword.strip():
        keywords.append(title_keyword.strip())

    if await _table_exists(db, "title_libraries") and await _table_exists(db, "keywords"):
        lib_row = (
            await db.execute(
                text("SELECT keyword_library_id FROM title_libraries WHERE id = :id"),
                {"id": task.title_library_id},
            )
        ).first()
        keyword_library_id = int(lib_row[0]) if lib_row and lib_row[0] else None
        if keyword_library_id:
            kw_rows = (
                await db.execute(
                    text(
                        """
                        SELECT keyword FROM keywords
                        WHERE library_id = :lid
                        ORDER BY RANDOM()
                        LIMIT 8
                        """
                    ),
                    {"lid": keyword_library_id},
                )
            ).all()
            keywords.extend(str(r[0]) for r in kw_rows if r[0])

    # 正文启发式补充
    for token in re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{4,}", content[:2000]):
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= 12:
            break

    seen: set[str] = set()
    deduped: list[str] = []
    for kw in keywords:
        key = kw.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(kw)
    return ", ".join(deduped[:12])


async def bump_ai_model_usage(db: AsyncSession, model_id: int | None) -> None:
    if not model_id:
        return
    model = await db.get(AiModel, model_id)
    if model is None:
        return
    model.used_today = int(model.used_today or 0) + 1
    model.total_used = int(model.total_used or 0) + 1
