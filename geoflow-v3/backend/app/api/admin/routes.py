"""Admin BFF API — geoflow-admin 专用。"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, get_admin_jwt
from app.api.response import success
from app.models.article import Article
from app.models.knowledge import KnowledgeBase
from app.models.task import Task
from app.models.tech_ip import TechIpAsset
from app.services.admin.materials_crud_service import (
    AuthorBody,
    CategoryBody,
    create_author,
    create_category,
    delete_author,
    delete_category,
    list_authors,
    list_categories,
    update_author,
    update_category,
)
from app.services.admin.distribution_form_service import (
    AdminDistributionCreateBody,
    build_distribution_form_options,
    create_admin_distribution_channel,
)
from app.services.admin.dashboard_service import build_dashboard_payload
from app.services.admin.operations_service import (
    build_articles_panel,
    build_distribution_panel,
    build_operations_overview,
    build_tasks_panel,
)
from app.services.admin.production_service import (
    build_ai_config_panel,
    build_knowledge_panel,
    build_materials_panel,
    build_production_overview,
)
from app.services.admin.article_form_service import (
    AdminArticleCreateBody,
    AdminArticleUpdateBody,
    build_article_detail,
    build_article_form_options,
    build_trashed_articles,
    create_admin_article,
    purge_admin_article,
    restore_admin_article,
    update_admin_article,
)
from app.services.admin.task_form_service import (
    AdminTaskCreateBody,
    AdminTaskUpdateBody,
    build_task_detail,
    build_task_form_options,
    create_admin_task,
    delete_admin_task,
    update_admin_task,
)
from app.services.admin.distribution_detail_service import (
    AdminDistributionUpdateBody,
    build_channel_detail,
    build_distribution_jobs,
    retry_distribution_job,
    toggle_channel_status,
    update_admin_distribution_channel,
)
from app.services.admin.materials_libraries_service import (
    ImageMetaBody,
    KeywordBody,
    LibraryBody,
    TitleBody,
    create_image_library,
    create_image_meta,
    create_keyword,
    create_keyword_library,
    create_title,
    create_title_library,
    delete_title,
    delete_title_library,
    list_image_libraries,
    list_images,
    list_keyword_libraries,
    list_keywords,
    list_title_libraries,
    list_titles,
    update_title_library,
)
from app.services.admin.knowledge_crud_service import KnowledgeBaseBody, create_knowledge_base, delete_knowledge_base, get_knowledge_base, list_knowledge_bases_detail, update_knowledge_base
from app.services.admin.ai_config_crud_service import AiModelBody, PromptBody, create_ai_model, create_prompt, delete_ai_model, delete_prompt, list_ai_models, list_prompts, test_ai_model, update_ai_model, update_prompt
from app.services.admin.url_import_service import UrlImportBody, list_url_import_history, run_url_import
from app.services.admin.strategy_crud_service import (
    BatchReevalBody,
    InsightTemplateBody,
    MonitorQuestionBody,
    WebSourceBody,
    apply_recommendations,
    batch_reevaluate,
    create_insight_template,
    create_monitor_question,
    create_web_source,
    delete_insight_template,
    delete_monitor_question,
    delete_web_source,
    list_insight_templates_crud,
    refresh_web_source,
    remine_insight_template,
    update_insight_template,
    update_monitor_question,
)
from app.services.admin.settings_crud_service import (
    AdminUserBody,
    ApiTokenBody,
    SensitiveWordsBody,
    SiteSettingBody,
    create_admin_user,
    create_api_token,
    get_sensitive_words,
    get_site_settings_full,
    list_activity_logs,
    list_admin_users,
    list_api_tokens,
    rotate_channel_secret,
    save_sensitive_words,
    upsert_site_setting,
)
from app.services.admin.strategy_service import (
    build_analytics_panel,
    build_geo_eval_panel,
    build_insight_templates,
    build_monitor_panel,
    build_strategy_overview,
    build_web_intel_panel,
)
from app.services.geoflow.article_publish import ArticlePublishService
from app.services.geoflow.task_lifecycle import TaskLifecycleService
from app.ws.tasks import broadcast_tasks_overview

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_dashboard_payload(db))


@router.get("/settings/site")
async def site_settings(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_site_settings_full(db))


@router.put("/settings/site")
async def update_site_setting(body: SiteSettingBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await upsert_site_setting(db, body))


@router.get("/settings/security/sensitive-words")
async def sensitive_words_get(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_sensitive_words(db))


@router.put("/settings/security/sensitive-words")
async def sensitive_words_put(body: SensitiveWordsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await save_sensitive_words(db, body))


@router.get("/settings/admins")
async def admins_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_admin_users(db))


@router.post("/settings/admins")
async def admins_create(body: AdminUserBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_admin_user(db, body), status=201)


@router.get("/settings/api-tokens")
async def api_tokens_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_api_tokens(db))


@router.post("/settings/api-tokens")
async def api_tokens_create(body: ApiTokenBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    admin_id = int(jwt.get("sub", 0) or 0)
    return success(request, await create_api_token(db, admin_id, body), status=201)


@router.get("/settings/activity-logs")
async def activity_logs(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_activity_logs(db))


@router.get("/operations/overview")
async def operations_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_operations_overview(db))


@router.get("/tasks")
async def list_tasks(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_tasks_panel(db))


@router.get("/tasks/form-options")
async def task_form_options(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_task_form_options(db))


@router.post("/tasks")
async def create_task(request: Request, body: AdminTaskCreateBody, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await create_admin_task(db, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_task_create_failed name=%s", body.task_name)
        raise HTTPException(status_code=500, detail="task_create_failed") from exc
    await broadcast_tasks_overview()
    return success(request, payload, status=201)


@router.get("/tasks/{task_id}")
async def show_task(task_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_task_detail(db, task_id))


@router.patch("/tasks/{task_id}")
async def patch_task(task_id: int, body: AdminTaskUpdateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await update_admin_task(db, task_id, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_task_update_failed task_id=%s", task_id)
        raise HTTPException(status_code=500, detail="task_update_failed") from exc
    await broadcast_tasks_overview()
    return success(request, payload)


@router.delete("/tasks/{task_id}")
async def remove_task(task_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    payload = await delete_admin_task(db, task_id)
    await broadcast_tasks_overview()
    return success(request, payload)


@router.get("/tasks/overview")
async def tasks_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    payload = await build_tasks_panel(db)
    recent_runs = []
    for task in payload["tasks"][:15]:
        if task.get("batch_status"):
            recent_runs.append(
                {
                    "id": task["id"],
                    "status": task["batch_status"],
                    "task_id": task["id"],
                }
            )
    return success(request, {"tasks": payload["tasks"], "recent_runs": recent_runs})


class EnqueueBody(BaseModel):
    task_id: int


@router.post("/tasks/enqueue")
async def admin_enqueue(body: EnqueueBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = TaskLifecycleService(db)
    try:
        run = await svc.enqueue(body.task_id)
    except ValueError as exc:
        logger.warning("task_enqueue_failed task_id=%s err=%s", body.task_id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_tasks_overview()
    return success(request, {"job": {"id": run.id, "status": run.status}})


@router.post("/tasks/{task_id}/start")
async def admin_start_task(task_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = TaskLifecycleService(db)
    try:
        task = await svc.start(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_tasks_overview()
    return success(request, {"task": _task_brief(task)})


@router.post("/tasks/{task_id}/stop")
async def admin_stop_task(task_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = TaskLifecycleService(db)
    try:
        task = await svc.stop(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_tasks_overview()
    return success(request, {"task": _task_brief(task)})


@router.post("/tasks/{task_id}/enqueue")
async def admin_enqueue_task(task_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = TaskLifecycleService(db)
    try:
        run = await svc.enqueue(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_tasks_overview()
    return success(request, {"job": {"id": run.id, "status": run.status}})


@router.get("/articles")
async def list_articles(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    review_status: str | None = Query(default=None),
):
    return success(request, await build_articles_panel(db, review_status=review_status))


@router.get("/articles/form-options")
async def article_form_options(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_article_form_options(db))


@router.post("/articles")
async def create_article(body: AdminArticleCreateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_admin_article(db, body), status=201)


@router.get("/articles/trash")
async def trashed_articles(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_trashed_articles(db))


@router.get("/articles/{article_id}")
async def show_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_article_detail(db, article_id))


@router.patch("/articles/{article_id}")
async def update_article(
    article_id: int,
    body: AdminArticleUpdateBody,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
):
    try:
        payload = await update_admin_article(db, body=body, article_id=article_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_article_update_failed article_id=%s", article_id)
        raise HTTPException(status_code=500, detail="article_update_failed") from exc
    return success(request, payload)


@router.post("/articles/{article_id}/review")
async def admin_review_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    article.review_status = "approved"
    return success(request, {"article": _article_brief(article)})


@router.post("/articles/{article_id}/publish")
async def admin_publish_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = ArticlePublishService(db)
    try:
        article = await svc.publish(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success(request, {"article": _article_brief(article)})


@router.post("/articles/{article_id}/trash")
async def admin_trash_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    article.deleted_at = datetime.now(UTC)
    article.status = "trashed"
    return success(request, {"article": _article_brief(article)})


@router.post("/articles/{article_id}/restore")
async def admin_restore_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await restore_admin_article(db, article_id))


@router.delete("/articles/{article_id}/purge")
async def admin_purge_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await purge_admin_article(db, article_id))


@router.get("/distribution")
async def distribution_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_distribution_panel(db))


@router.get("/distribution/form-options")
async def distribution_form_options(request: Request, jwt=Depends(get_admin_jwt)):
    return success(request, build_distribution_form_options())


@router.post("/distribution/channels")
async def create_distribution_channel(
    body: AdminDistributionCreateBody,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
):
    try:
        payload = await create_admin_distribution_channel(db, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_distribution_create_failed name=%s", body.name)
        raise HTTPException(status_code=500, detail="distribution_create_failed") from exc
    return success(request, payload, status=201)


@router.get("/distribution/channels/{channel_id}")
async def show_distribution_channel(channel_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_channel_detail(db, channel_id))


@router.patch("/distribution/channels/{channel_id}")
async def patch_distribution_channel(
    channel_id: int, body: AdminDistributionUpdateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    channel = await update_admin_distribution_channel(db, channel_id, body)
    return success(request, {"channel": channel})


@router.post("/distribution/channels/{channel_id}/{action}")
async def distribution_channel_action(
    channel_id: int, action: str, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    if action not in ("pause", "activate"):
        raise HTTPException(status_code=422, detail="invalid_action")
    return success(request, await toggle_channel_status(db, channel_id, action))


@router.get("/distribution/jobs")
async def distribution_jobs(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    channel_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
):
    return success(request, await build_distribution_jobs(db, channel_id=channel_id, status=status))


@router.post("/distribution/jobs/{job_id}/retry")
async def retry_job(job_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await retry_distribution_job(db, job_id))


@router.post("/distribution/channels/{channel_id}/rotate-secret")
async def rotate_secret(channel_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await rotate_channel_secret(db, channel_id))


@router.get("/production/overview")
async def production_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_production_overview(db))


@router.get("/production/materials")
async def production_materials(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_materials_panel(db))


@router.get("/materials/categories")
async def materials_categories_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_categories(db))


@router.post("/materials/categories")
async def materials_categories_create(body: CategoryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_category(db, body), status=201)


@router.patch("/materials/categories/{category_id}")
async def materials_categories_update(
    category_id: int, body: CategoryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await update_category(db, category_id, body))


@router.delete("/materials/categories/{category_id}")
async def materials_categories_delete(category_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_category(db, category_id))


@router.get("/materials/authors")
async def materials_authors_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_authors(db))


@router.post("/materials/authors")
async def materials_authors_create(body: AuthorBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_author(db, body), status=201)


@router.patch("/materials/authors/{author_id}")
async def materials_authors_update(
    author_id: int, body: AuthorBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await update_author(db, author_id, body))


@router.delete("/materials/authors/{author_id}")
async def materials_authors_delete(author_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_author(db, author_id))


@router.get("/production/knowledge")
async def production_knowledge(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_knowledge_panel(db))


@router.get("/production/ai-config")
async def production_ai_config(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_ai_config_panel(db))


@router.get("/strategy/overview")
async def strategy_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_strategy_overview(db))


@router.get("/strategy/monitor")
async def strategy_monitor(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_monitor_panel(db))


@router.post("/strategy/monitor/scan")
async def strategy_monitor_scan(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.run_monitor_scan", args=["daily"])
    logger.info("admin_monitor_scan_queued")
    return success(request, {"queued": True})


@router.get("/strategy/geo-eval")
async def strategy_geo_eval(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_geo_eval_panel(db))


@router.post("/strategy/geo-eval/reevaluate/{article_id}")
async def strategy_reevaluate_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.evaluate_article", args=[article_id])
    return success(request, {"queued": True, "article_id": article_id})


@router.get("/strategy/analytics")
async def strategy_analytics(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_analytics_panel(db))


@router.get("/strategy/web-intel")
async def strategy_web_intel(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_web_intel_panel(db))


@router.get("/strategy/insight-templates")
async def strategy_insight_templates(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_insight_templates(db))


@router.get("/tech-assets")
async def list_tech_assets(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    rows = (await db.execute(select(TechIpAsset).order_by(TechIpAsset.priority))).scalars().all()
    return success(request, {"items": [_asset_dict(a) for a in rows]})


class TechAssetBody(BaseModel):
    ip_id: str
    name: str
    mind_tag: str = ""
    wiki_type: str = "concept"
    priority: int = 100


@router.post("/tech-assets")
async def create_tech_asset(body: TechAssetBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    asset = TechIpAsset(**body.model_dump())
    db.add(asset)
    await db.flush()
    return success(request, {"item": _asset_dict(asset)}, status=201)


@router.get("/knowledge-bases")
async def list_knowledge_bases(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    rows = (await db.execute(select(KnowledgeBase))).scalars().all()
    return success(request, {"items": [{"id": k.id, "name": k.name} for k in rows]})


@router.post("/knowledge-bases/{kb_id}/sync-chunks")
async def sync_kb_chunks(kb_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.sync_knowledge_chunks", args=[kb_id])
    return success(request, {"queued": True, "knowledge_base_id": kb_id})


@router.get("/knowledge-bases/detail")
async def knowledge_bases_detail(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_knowledge_bases_detail(db))


@router.get("/knowledge-bases/{kb_id}/detail")
async def knowledge_base_detail(kb_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_knowledge_base(db, kb_id))


@router.post("/knowledge-bases/create")
async def knowledge_base_create(body: KnowledgeBaseBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_knowledge_base(db, body), status=201)


@router.patch("/knowledge-bases/{kb_id}")
async def knowledge_base_update(kb_id: int, body: KnowledgeBaseBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_knowledge_base(db, kb_id, body))


@router.delete("/knowledge-bases/{kb_id}")
async def knowledge_base_delete(kb_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_knowledge_base(db, kb_id))


@router.get("/ai-models")
async def ai_models_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_ai_models(db))


@router.post("/ai-models")
async def ai_models_create(body: AiModelBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_ai_model(db, body), status=201)


@router.patch("/ai-models/{model_id}")
async def ai_models_update(model_id: int, body: AiModelBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_ai_model(db, model_id, body))


@router.delete("/ai-models/{model_id}")
async def ai_models_delete(model_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_ai_model(db, model_id))


@router.post("/ai-models/{model_id}/test")
async def ai_models_test(model_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await test_ai_model(db, model_id))


@router.get("/prompts")
async def prompts_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_prompts(db))


@router.post("/prompts")
async def prompts_create(body: PromptBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_prompt(db, body), status=201)


@router.patch("/prompts/{prompt_id}")
async def prompts_update(prompt_id: int, body: PromptBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_prompt(db, prompt_id, body))


@router.delete("/prompts/{prompt_id}")
async def prompts_delete(prompt_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_prompt(db, prompt_id))


@router.get("/materials/title-libraries")
async def title_libraries_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_title_libraries(db))


@router.post("/materials/title-libraries")
async def title_libraries_create(body: LibraryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_title_library(db, body), status=201)


@router.patch("/materials/title-libraries/{library_id}")
async def title_libraries_update(library_id: int, body: LibraryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_title_library(db, library_id, body))


@router.delete("/materials/title-libraries/{library_id}")
async def title_libraries_delete(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_title_library(db, library_id))


@router.get("/materials/title-libraries/{library_id}/titles")
async def titles_list(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_titles(db, library_id))


@router.post("/materials/title-libraries/{library_id}/titles")
async def titles_create(library_id: int, body: TitleBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_title(db, library_id, body), status=201)


@router.delete("/materials/titles/{title_id}")
async def titles_delete(title_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_title(db, title_id))


@router.get("/materials/keyword-libraries")
async def keyword_libraries_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_keyword_libraries(db))


@router.post("/materials/keyword-libraries")
async def keyword_libraries_create(body: LibraryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_keyword_library(db, body), status=201)


@router.get("/materials/keyword-libraries/{library_id}/keywords")
async def keywords_list(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_keywords(db, library_id))


@router.post("/materials/keyword-libraries/{library_id}/keywords")
async def keywords_create(library_id: int, body: KeywordBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_keyword(db, library_id, body), status=201)


@router.get("/materials/image-libraries")
async def image_libraries_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_image_libraries(db))


@router.post("/materials/image-libraries")
async def image_libraries_create(body: LibraryBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_image_library(db, body), status=201)


@router.get("/materials/image-libraries/{library_id}/images")
async def images_list(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_images(db, library_id))


@router.post("/materials/image-libraries/{library_id}/images")
async def images_create(library_id: int, body: ImageMetaBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_image_meta(db, library_id, body), status=201)


@router.post("/production/url-import")
async def url_import_run(body: UrlImportBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await run_url_import(db, body), status=201)


@router.get("/production/url-import/history")
async def url_import_history(request: Request, jwt=Depends(get_admin_jwt)):
    return success(request, await list_url_import_history())


@router.get("/strategy/insight-templates/manage")
async def insight_templates_manage(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_insight_templates_crud(db))


@router.post("/strategy/insight-templates")
async def insight_templates_create(body: InsightTemplateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_insight_template(db, body), status=201)


@router.patch("/strategy/insight-templates/{template_id}")
async def insight_templates_update(template_id: int, body: InsightTemplateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_insight_template(db, template_id, body))


@router.delete("/strategy/insight-templates/{template_id}")
async def insight_templates_delete(template_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_insight_template(db, template_id))


@router.post("/strategy/insight-templates/{template_id}/re-mine")
async def insight_templates_remine(template_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await remine_insight_template(db, template_id))


@router.post("/strategy/monitor/questions")
async def monitor_questions_create(body: MonitorQuestionBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_monitor_question(db, body), status=201)


@router.patch("/strategy/monitor/questions/{question_id}")
async def monitor_questions_update(question_id: int, body: MonitorQuestionBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_monitor_question(db, question_id, body))


@router.delete("/strategy/monitor/questions/{question_id}")
async def monitor_questions_delete(question_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_monitor_question(db, question_id))


@router.post("/strategy/web-intel/sources")
async def web_sources_create(body: WebSourceBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_web_source(db, body), status=201)


@router.delete("/strategy/web-intel/sources/{source_id}")
async def web_sources_delete(source_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_web_source(db, source_id))


@router.post("/strategy/web-intel/sources/{source_id}/refresh")
async def web_sources_refresh(source_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await refresh_web_source(db, source_id))


@router.post("/strategy/simulator/batch-reevaluate")
async def simulator_batch_reevaluate(body: BatchReevalBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await batch_reevaluate(db, body))


@router.post("/strategy/simulator/apply-recommendations/{article_id}")
async def simulator_apply_recommendations(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await apply_recommendations(db, article_id))


@router.patch("/tech-assets/{asset_id}")
async def update_tech_asset(asset_id: int, body: TechAssetBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    asset = await db.get(TechIpAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset_not_found")
    for k, v in body.model_dump().items():
        setattr(asset, k, v)
    await db.flush()
    return success(request, {"item": _asset_dict(asset)})


def _task_brief(task: Task) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "created_count": task.created_count,
        "published_count": task.published_count,
    }


def _article_brief(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "status": article.status,
        "review_status": article.review_status,
    }


def _asset_dict(a: TechIpAsset) -> dict:
    return {
        "id": a.id,
        "ip_id": a.ip_id,
        "name": a.name,
        "mind_tag": a.mind_tag,
        "wiki_type": a.wiki_type,
        "wiki_slug": a.wiki_slug,
        "priority": a.priority,
        "status": a.status,
    }
