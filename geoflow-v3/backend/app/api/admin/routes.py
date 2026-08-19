"""Admin BFF API — geoflow-admin 专用。"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
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
from app.services.admin.batch_operations_service import BatchIdsBody, batch_publish_articles, batch_start_tasks, batch_trash_articles
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
from app.services.admin.wiki_editor_schema import WikiGenerateDraftBody, WikiPageBody
from app.services.admin.wiki_editor_service import (
    build_wiki_detail,
    build_wiki_packs,
    build_wiki_panel,
    create_wiki_page,
    generate_wiki_draft,
    import_geoweb_wiki_pages,
    list_wiki_related_options,
    publish_wiki_page,
    reconcile_wiki_with_geoweb,
    sync_wiki_pack,
    update_wiki_page,
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
from app.services.admin.distribution_citation_service import (
    build_article_citation_detail,
    build_distribution_citation_overview,
    build_distributed_article_citations,
    refresh_distribution_citation_cache,
)
from app.services.admin.distribution_detail_service import (
    AdminDistributionBatchBody,
    AdminDistributionUpdateBody,
    DistributionJobUpdateBody,
    build_channel_detail,
    build_distribution_jobs,
    check_channel_health,
    create_distribution_batch,
    delete_admin_distribution_channel,
    delete_distribution_job,
    retry_distribution_job,
    toggle_channel_status,
    update_admin_distribution_channel,
    update_distribution_job,
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
    delete_image,
    delete_image_library,
    delete_keyword,
    delete_keyword_library,
    delete_title,
    delete_title_library,
    list_image_libraries,
    list_images,
    list_keyword_libraries,
    list_keywords,
    list_title_libraries,
    list_titles,
    update_title_library,
    bulk_create_titles,
    generate_titles,
    BulkTitlesBody,
    TitleGenerateBody,
)
from app.services.admin.knowledge_settings_service import (
    KnowledgeSettingsBody,
    RagSandboxBody,
    get_knowledge_settings,
    run_rag_sandbox,
    save_knowledge_settings,
)
from app.services.admin.tech_assets_import_service import TechYamlImportBody, import_tech_assets_yaml
from app.services.admin.upload_service import read_knowledge_upload, save_image_upload
from app.services.admin.knowledge_crud_service import KnowledgeBaseBody, append_knowledge_file_content, create_knowledge_base, delete_knowledge_base, get_knowledge_base, list_knowledge_bases_detail, update_knowledge_base
from app.services.geoflow.rag.knowledge_sync_queue import queue_knowledge_chunk_sync
from app.services.admin.ai_config_crud_service import AiModelBody, PromptBody, create_ai_model, create_prompt, delete_ai_model, delete_prompt, list_ai_models, list_prompts, test_ai_model, update_ai_model, update_prompt
from app.services.admin.agent_config_service import (
    AgentUpdateBody,
    get_agent as get_agent_config,
    list_agents,
    update_agent as update_agent_config,
)
from app.services.admin.monitor_detail_service import build_monitor_run_detail, list_monitor_runs
from app.services.admin.monitor_aivis_service import (
    CompetitorBody,
    MonitorSceneBody,
    QueryTemplateBody,
    create_competitor,
    create_monitor_scene,
    create_product,
    create_query_template,
    generate_questions_from_template,
    list_competitors,
    list_products,
    list_monitor_insights,
    list_monitor_scenes,
    list_monitor_snapshots,
    list_query_templates,
    list_visibility_reports,
)
from app.services.admin.geo_eval_settings_service import GeoEvalSettingsBody, save_geo_eval_settings
from app.services.admin.monitor_settings_service import MonitorSettingsBody, get_monitor_settings, save_monitor_settings
from app.services.admin.url_import_service import UrlImportBody, commit_url_import_job, get_url_import_job, list_url_import_history, run_url_import
from app.services.admin.strategy_crud_service import (
    BatchReevalBody,
    InsightTemplateBody,
    MonitorQuestionBody,
    MonitorQuestionBulkBody,
    WebSourceBody,
    apply_recommendations,
    batch_reevaluate,
    bulk_import_monitor_questions,
    create_insight_template,
    create_monitor_question,
    create_web_source,
    delete_insight_template,
    delete_monitor_question,
    delete_web_source,
    list_insight_templates_crud,
    list_monitor_questions,
    refresh_web_source,
    seed_default_brand_questions,
    remine_insight_template,
    update_insight_template,
    update_monitor_question,
)
from app.services.admin.settings_crud_service import (
    AdminUserBody,
    AdminUserUpdateBody,
    ApiTokenBody,
    PasswordChangeBody,
    SensitiveWordsBody,
    SiteSettingBody,
    change_admin_password,
    create_admin_user,
    create_api_token,
    delete_admin_user,
    get_sensitive_words,
    get_site_settings_full,
    list_activity_logs,
    list_admin_users,
    list_api_tokens,
    revoke_api_token,
    rotate_channel_secret,
    save_sensitive_words,
    toggle_admin_user,
    update_admin_user,
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
from app.services.admin.aivis_service import (
    build_brand_panel,
    build_collection_panel,
    build_diagnosis_panel,
    build_product_panel,
)
from app.services.geoeval.aivis_analyzers import assess_difficulty, build_optimization_panel
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


@router.patch("/settings/admins/{admin_id}")
async def admins_update(admin_id: int, body: AdminUserUpdateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await update_admin_user(db, admin_id, body))


@router.post("/settings/admins/{admin_id}/toggle-status")
async def admins_toggle(admin_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await toggle_admin_user(db, admin_id))


@router.delete("/settings/admins/{admin_id}")
async def admins_delete(admin_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_admin_user(db, admin_id))


@router.post("/settings/security/password")
async def security_password(body: PasswordChangeBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    admin_id = int(jwt.get("sub", 0) or 0)
    return success(request, await change_admin_password(db, admin_id, body))


@router.get("/settings/api-tokens")
async def api_tokens_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_api_tokens(db))


@router.post("/settings/api-tokens")
async def api_tokens_create(body: ApiTokenBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    admin_id = int(jwt.get("sub", 0) or 0)
    return success(request, await create_api_token(db, admin_id, body), status=201)


@router.post("/settings/api-tokens/{token_id}/revoke")
async def api_tokens_revoke(token_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await revoke_api_token(db, token_id))


@router.get("/settings/activity-logs")
async def activity_logs(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_activity_logs(db))


@router.get("/operations/overview")
async def operations_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_operations_overview(db))


@router.get("/tasks")
async def list_tasks(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    theme_id: int | None = Query(default=None),
):
    return success(request, await build_tasks_panel(db, theme_id=theme_id))


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


@router.post("/tasks/batch/start")
async def batch_tasks_start(body: BatchIdsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await batch_start_tasks(db, body))


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
    theme_id: int | None = Query(default=None),
):
    return success(request, await build_articles_panel(db, review_status=review_status, theme_id=theme_id))


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


@router.post("/articles/batch/trash")
async def batch_articles_trash(body: BatchIdsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await batch_trash_articles(db, body))


@router.post("/articles/batch/publish")
async def batch_articles_publish(body: BatchIdsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await batch_publish_articles(db, body))


@router.get("/wiki")
async def list_wiki_pages(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    wiki_page_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    include_smoke: bool = Query(default=False),
):
    return success(
        request,
        await build_wiki_panel(db, page_type=wiki_page_type, q=q, include_smoke=include_smoke),
    )


@router.post("/wiki/import-geoweb")
async def import_wiki_from_geoweb(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await import_geoweb_wiki_pages(db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_import_failed")
        raise HTTPException(status_code=500, detail="wiki_import_failed") from exc
    return success(request, payload)


@router.get("/wiki/related-options")
async def wiki_related_options(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    exclude_id: int | None = Query(default=None),
):
    return success(request, await list_wiki_related_options(db, exclude_id=exclude_id))


@router.post("/wiki/generate-draft")
async def wiki_generate_draft(
    body: WikiGenerateDraftBody,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
):
    try:
        payload = await generate_wiki_draft(db, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_generate_draft_failed")
        raise HTTPException(status_code=500, detail="wiki_generate_draft_failed") from exc
    return success(request, payload)


@router.get("/wiki/packs")
async def wiki_packs(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_wiki_packs(db))


@router.post("/wiki/packs/{theme_id}/sync-pack")
async def wiki_sync_pack(theme_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await sync_wiki_pack(db, theme_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_sync_pack_failed theme_id=%s", theme_id)
        raise HTTPException(status_code=500, detail="wiki_sync_pack_failed") from exc
    return success(request, payload)


@router.get("/wiki/reconcile")
async def wiki_reconcile(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await reconcile_wiki_with_geoweb(db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_reconcile_failed")
        raise HTTPException(status_code=500, detail="wiki_reconcile_failed") from exc
    return success(request, payload)


@router.post("/wiki")
async def create_wiki_admin_page(body: WikiPageBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await create_wiki_page(db, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_create_failed")
        raise HTTPException(status_code=500, detail="wiki_create_failed") from exc
    return success(request, payload, status=201)


@router.get("/wiki/{article_id}")
async def show_wiki_page(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_wiki_detail(db, article_id))


@router.patch("/wiki/{article_id}")
async def update_wiki_admin_page(
    article_id: int,
    body: WikiPageBody,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
):
    try:
        payload = await update_wiki_page(db, article_id, body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_update_failed article_id=%s", article_id)
        raise HTTPException(status_code=500, detail="wiki_update_failed") from exc
    return success(request, payload)


@router.post("/wiki/{article_id}/publish")
async def publish_wiki_admin_page(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        payload = await publish_wiki_page(db, article_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_wiki_publish_failed article_id=%s", article_id)
        raise HTTPException(status_code=500, detail="wiki_publish_failed") from exc
    return success(request, payload)


@router.get("/distribution")
async def distribution_overview(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    theme_id: int | None = Query(default=None),
):
    return success(request, await build_distribution_panel(db, theme_id=theme_id))


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
    theme_id: int | None = Query(default=None),
):
    return success(
        request,
        await build_distribution_jobs(db, channel_id=channel_id, status=status, theme_id=theme_id),
    )


@router.post("/distribution/batch")
async def distribution_batch(
    body: AdminDistributionBatchBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    try:
        payload = await create_distribution_batch(db, body)
        return success(request, payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("admin_distribution_batch_failed")
        raise HTTPException(status_code=500, detail="distribution_batch_failed") from exc


@router.post("/distribution/jobs/{job_id}/retry")
async def retry_job(job_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await retry_distribution_job(db, job_id))


@router.patch("/distribution/jobs/{job_id}")
async def patch_distribution_job(
    job_id: int, body: DistributionJobUpdateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await update_distribution_job(db, job_id, body))


@router.delete("/distribution/jobs/{job_id}")
async def delete_distribution_job_route(job_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_distribution_job(db, job_id))


@router.get("/distribution/citations/overview")
async def distribution_citations_overview(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    days: int = Query(default=7, ge=1, le=90),
):
    try:
        return success(request, await build_distribution_citation_overview(db, days=days))
    except Exception as exc:
        logger.exception("distribution_citations_overview_failed days=%s", days)
        raise HTTPException(status_code=500, detail="distribution_citations_overview_failed") from exc


@router.get("/distribution/citations/articles")
async def distribution_citations_articles(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    status: str = Query(default="all", pattern="^(all|indexed|not_indexed|pending_scan)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
):
    try:
        return success(
            request,
            await build_distributed_article_citations(db, status=status, page=page, per_page=per_page),
        )
    except Exception as exc:
        logger.exception("distribution_citations_articles_failed status=%s", status)
        raise HTTPException(status_code=500, detail="distribution_citations_articles_failed") from exc


@router.get("/distribution/citations/articles/{article_id}")
async def distribution_citations_article_detail(
    article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    try:
        return success(request, await build_article_citation_detail(db, article_id))
    except Exception as exc:
        logger.exception("distribution_citations_detail_failed article_id=%s", article_id)
        raise HTTPException(status_code=500, detail="distribution_citations_detail_failed") from exc


@router.post("/distribution/citations/refresh")
async def distribution_citations_refresh(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    try:
        return success(request, await refresh_distribution_citation_cache(db))
    except Exception as exc:
        logger.exception("distribution_citations_refresh_failed")
        raise HTTPException(status_code=500, detail="distribution_citations_refresh_failed") from exc


@router.delete("/distribution/channels/{channel_id}")
async def delete_distribution_channel(channel_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_admin_distribution_channel(db, channel_id))


@router.get("/distribution/channels/{channel_id}/health")
async def distribution_channel_health(channel_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await check_channel_health(db, channel_id))


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


@router.get("/strategy/diagnosis")
async def strategy_diagnosis(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_diagnosis_panel(db))


@router.get("/strategy/collection")
async def strategy_collection(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_collection_panel(db))


@router.get("/strategy/brand")
async def strategy_brand(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_brand_panel(db))


@router.get("/strategy/product")
async def strategy_product(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_product_panel(db))


@router.get("/strategy/optimization")
async def strategy_optimization(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_optimization_panel(db))


@router.get("/strategy/difficulty")
async def strategy_difficulty(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await assess_difficulty(db))


@router.get("/strategy/monitor")
async def strategy_monitor(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_monitor_panel(db))


@router.post("/strategy/monitor/scan")
async def strategy_monitor_scan(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    scan_type: str = Query(default="daily", pattern="^(daily|market)$"),
):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.run_monitor_scan", args=[scan_type])
    logger.info("admin_monitor_scan_queued scan_type=%s", scan_type)
    return success(request, {"queued": True, "scan_type": scan_type})


class CendScanBody(BaseModel):
    platforms: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=20)
    min_priority: int = Field(default=80, ge=0, le=100)
    sync: bool = False  # True 时进程内执行（联调/Mock）；默认入队


class CendIngestBody(BaseModel):
    """手工导入一条完整 C 端捕获（契约验收 / 无浏览器时）。"""

    question_id: int
    platform: str
    answer_text: str = ""
    thinking_text: str = ""
    thinking_ms: int | None = None
    citations: list[dict] | None = None  # [{title,url,position}]
    keywords: list[str] | None = None
    rank_blocks: list[dict] | None = None
    decision_table: list[dict] | None = None
    source_hosts: list[str] | None = None
    brand_list: list[str] | None = None
    competitor_brands: list[str] | None = None
    capture_artifact: str | None = None
    write_gold: bool = True


@router.post("/strategy/cend/scan")
async def strategy_cend_scan(body: CendScanBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    if body.sync:
        from app.services.geoeval.cend_scan import CendScanOrchestrator

        result = await CendScanOrchestrator(db).run_scan(
            platforms=body.platforms,
            limit=body.limit,
            min_priority=body.min_priority,
        )
        logger.info("admin_cend_scan_sync platforms=%s probes=%s", body.platforms, result.get("probes"))
        return success(request, result)

    celery_app.send_task(
        "app.workers.tasks.run_cend_probe_scan",
        kwargs={
            "platforms": body.platforms,
            "limit": body.limit,
            "min_priority": body.min_priority,
        },
    )
    logger.info("admin_cend_scan_queued platforms=%s limit=%s", body.platforms, body.limit)
    return success(request, {"queued": True, "scan_type": "cend", "platforms": body.platforms, "limit": body.limit})


@router.get("/strategy/cend/platforms")
async def strategy_cend_platforms(request: Request, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.platform_connectors.cend.registry import list_cend_platforms
    from app.services.geoeval.platform_connectors.base import CEND_PLATFORM_URLS

    items = [
        {"platform": p, "start_url": CEND_PLATFORM_URLS.get(p, ""), "label": p}
        for p in list_cend_platforms()
    ]
    return success(request, {"platforms": items, "metric_kind": "cend_sample"})


@router.get("/strategy/cend/profile-status")
async def strategy_cend_profile_status(
    request: Request,
    jwt=Depends(get_admin_jwt),
    platform: str = Query(default="yuanbao"),
):
    from app.services.geoeval.platform_connectors.cend.browser_session import check_profile_ready

    return success(request, await check_profile_ready(platform))


@router.post("/strategy/cend/ingest")
async def strategy_cend_ingest(body: CendIngestBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    """手工写入一条 cend_browser 探针结果（Phase1 契约验收）。"""
    from app.services.geoeval.answer_parser import PARSER_VERSION, parse_answer
    from app.services.geoeval.monitor_probe import _persist_probe, load_brand_keywords
    from app.services.geoeval.platform_connectors.base import ProbeOutcome, calc_ranking_score
    from app.services.admin.production_service import _table_exists
    from sqlalchemy import text as sa_text

    brands = body.brand_list or await load_brand_keywords(db)
    answer = body.answer_text or ""
    parsed = parse_answer(answer, brand_list=brands, competitor_brands=body.competitor_brands)
    cites = body.citations or []
    cite_urls = [str(c.get("url") or "") for c in cites if c.get("url")]
    cite_titles = [str(c.get("title") or "") for c in cites]

    run_id = None
    if await _table_exists(db, "geo_monitor_runs"):
        row = (
            await db.execute(
                sa_text(
                    """
                    INSERT INTO geo_monitor_runs (status, platform, question_count, probe_count, started_at, completed_at)
                    VALUES ('completed', :plat, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                    """
                ),
                {"plat": f"cend-ingest:{body.platform}"[:200]},
            )
        ).first()
        run_id = int(row[0]) if row else None

    outcome = ProbeOutcome(
        question_id=body.question_id,
        platform=body.platform,
        brand_rank=parsed.brand_rank if parsed.mentioned else None,
        mentioned=parsed.mentioned,
        snippet=answer[:240],
        engine="cend_browser",
        ranking_score=calc_ranking_score(parsed.brand_rank if parsed.mentioned else None),
        competitor_mentions=list(parsed.competitor_mentions),
        rank_method=parsed.rank_method,
        evidence_level="L2" if cite_urls else "L0",
        match_type=parsed.match_type,
        parser_version=PARSER_VERSION,
        urls=cite_urls or list(parsed.urls),
        thinking_text=body.thinking_text or None,
        thinking_ms=body.thinking_ms,
        keywords=body.keywords or [],
        entities=brands[:12],
        rank_blocks=body.rank_blocks or [],
        decision_table=body.decision_table or [],
        citation_urls=cite_urls,
        citation_titles=cite_titles,
        source_hosts=body.source_hosts or [],
        capture_artifact=body.capture_artifact,
        metric_kind="cend_sample",
        cend_meta={"ingest": True},
    )
    probe_id = None
    if run_id:
        probe_id = await _persist_probe(db, run_id=run_id, outcome=outcome)

    if body.write_gold and await _table_exists(db, "geo_probe_gold_labels"):
        from app.services.geoeval.cend_scan import CendScanOrchestrator

        await CendScanOrchestrator(db)._upsert_gold(body.question_id, body.platform, outcome, probe_id)

    from app.services.admin.distribution_citation_service import refresh_distribution_citation_cache

    cache = await refresh_distribution_citation_cache(db)
    logger.info(
        "admin_cend_ingest platform=%s question_id=%s probe_id=%s citations=%s",
        body.platform,
        body.question_id,
        probe_id,
        len(cite_urls),
    )
    return success(
        request,
        {
            "probe_id": probe_id,
            "run_id": run_id,
            "metric_kind": "cend_sample",
            "evidence_level": outcome.evidence_level,
            "mentioned": outcome.mentioned,
            "brand_rank": outcome.brand_rank,
            "citation_count": len(cite_urls),
            "indexed_count": cache.get("indexed_count", 0),
        },
        status=201,
    )


@router.get("/strategy/monitor/scenes")
async def strategy_monitor_scenes_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_monitor_scenes(db))


@router.post("/strategy/monitor/scenes")
async def strategy_monitor_scenes_create(body: MonitorSceneBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_monitor_scene(db, body), status=201)


@router.post("/strategy/monitor/scenes/{scene_id}/compute-gap")
async def strategy_monitor_scene_gap(scene_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.scene_gap_analyzer import compute_scene_gap

    return success(request, await compute_scene_gap(db, scene_id))


@router.post("/strategy/monitor/scenes/{scene_id}/create-task")
async def strategy_monitor_scene_create_task(
    scene_id: int,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    legacy_direct_task: bool = Query(False),
):
    """默认创建 Theme 草稿；legacy_direct_task=true 保留旧「直接建 Task」（弃用）。"""
    from app.services.geoeval.gap_task_generator import create_task_from_scene_gap

    return success(
        request,
        await create_task_from_scene_gap(db, scene_id, legacy_direct_task=legacy_direct_task),
        status=201,
    )


@router.get("/themes")
async def themes_list(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    status: str | None = Query(None),
):
    from app.services.geoeval.theme_service import list_themes

    return success(request, await list_themes(db, status=status))


@router.get("/themes/funnel")
async def themes_funnel(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import theme_funnel_stats

    return success(request, await theme_funnel_stats(db))


@router.get("/themes/analytics")
async def themes_analytics(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import analytics_by_theme

    return success(request, await analytics_by_theme(db))


@router.post("/themes")
async def themes_create(body: dict, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import ThemeCreateBody, create_theme

    payload = ThemeCreateBody.model_validate(body)
    return success(request, await create_theme(db, payload), status=201)


@router.post("/themes/from-scene/{scene_id}")
async def themes_from_scene(scene_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import create_theme_from_scene

    return success(request, await create_theme_from_scene(db, scene_id), status=201)


@router.get("/themes/{theme_id}")
async def themes_get(theme_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import get_theme

    return success(request, await get_theme(db, theme_id))


@router.patch("/themes/{theme_id}")
async def themes_patch(theme_id: int, body: dict, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import ThemePatchBody, patch_theme

    payload = ThemePatchBody.model_validate(body)
    return success(request, await patch_theme(db, theme_id, payload))


@router.post("/themes/{theme_id}/confirm")
async def themes_confirm(theme_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import confirm_theme

    return success(request, await confirm_theme(db, theme_id))


@router.post("/themes/{theme_id}/start-produce")
async def themes_start_produce(theme_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import start_produce

    return success(request, await start_produce(db, theme_id))


@router.post("/themes/{theme_id}/spawn-candidate")
async def themes_spawn_candidate(
    theme_id: int,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    candidate_index: int = Query(0, ge=0, le=9),
):
    from app.services.geoeval.theme_service import spawn_theme_candidate

    return success(request, await spawn_theme_candidate(db, theme_id, candidate_index), status=201)


@router.post("/themes/{theme_id}/refresh-gate")
async def themes_refresh_gate(theme_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.theme_service import refresh_theme_gate_summary

    return success(request, await refresh_theme_gate_summary(db, theme_id))


@router.get("/strategy/monitor/remediations")
async def strategy_monitor_remediations_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.remediation_service import list_remediations

    return success(request, await list_remediations(db))


@router.post("/strategy/monitor/remediations/process-due")
async def strategy_monitor_remediations_process_due(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.remediation_service import process_due_remediations

    return success(request, await process_due_remediations(db))


@router.post("/strategy/monitor/remediations/{remediation_id}/rescan")
async def strategy_monitor_remediation_rescan(
    remediation_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    from app.services.geoeval.remediation_service import complete_remediation_rescan

    return success(request, await complete_remediation_rescan(db, remediation_id))


@router.get("/strategy/monitor/geoweb-alignment")
async def strategy_monitor_geoweb_alignment(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.geoweb_alignment_service import compute_geoweb_alignment

    return success(request, await compute_geoweb_alignment(db))


@router.get("/strategy/monitor/gweb-alignment")
async def strategy_monitor_gweb_alignment_compat(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    """兼容旧路径 → GEOweb 对齐。"""
    from app.services.geoeval.geoweb_alignment_service import compute_geoweb_alignment

    return success(request, await compute_geoweb_alignment(db))


@router.get("/strategy/monitor/scenes/{scene_id}/citation-chain")
async def strategy_monitor_scene_citation_chain(scene_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.citation_chain_service import get_scene_citation_chain

    return success(request, await get_scene_citation_chain(db, scene_id))


@router.get("/strategy/monitor/questions/{question_id}/citations")
async def strategy_monitor_question_citations(question_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.citation_chain_service import get_question_citation_detail

    return success(request, await get_question_citation_detail(db, question_id))


@router.get("/strategy/monitor/templates")
async def strategy_monitor_templates_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_query_templates(db))


@router.post("/strategy/monitor/templates")
async def strategy_monitor_templates_create(body: QueryTemplateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_query_template(db, body), status=201)


@router.post("/strategy/monitor/templates/{template_id}/generate")
async def strategy_monitor_templates_generate(
    template_id: int,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    limit: int = Query(default=20, ge=1, le=100),
):
    return success(request, await generate_questions_from_template(db, template_id, limit))


@router.get("/strategy/monitor/competitors")
async def strategy_monitor_competitors_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_competitors(db))


@router.post("/strategy/monitor/competitors")
async def strategy_monitor_competitors_create(body: CompetitorBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_competitor(db, body), status=201)


@router.get("/strategy/monitor/products")
async def strategy_monitor_products_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_products(db))


@router.post("/strategy/monitor/products")
async def strategy_monitor_products_create(body: CompetitorBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await create_product(db, body), status=201)


@router.get("/strategy/monitor/snapshots")
async def strategy_monitor_snapshots_list(
    request: Request, db: DbSession, jwt=Depends(get_admin_jwt), days: int = Query(default=30, ge=7, le=90)
):
    return success(request, await list_monitor_snapshots(db, days))


@router.get("/strategy/monitor/insights")
async def strategy_monitor_insights_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_monitor_insights(db))


@router.get("/strategy/monitor/reports")
async def strategy_monitor_reports_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_visibility_reports(db))


@router.post("/strategy/monitor/reports/generate")
async def strategy_monitor_reports_generate(
    request: Request, db: DbSession, jwt=Depends(get_admin_jwt), period_days: int = Query(default=7, ge=1, le=90)
):
    from app.services.geoeval.report_composer import compose_visibility_report

    return success(request, await compose_visibility_report(db, period_days), status=201)


@router.post("/strategy/monitor/reports/import/tjg")
async def strategy_monitor_reports_import_tjg(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    token: str | None = Query(default=None),
    share_url: str | None = Query(default=None),
    replace_existing: bool = Query(default=False),
):
    from app.services.geoeval.tjg_report_parser import (
        import_tjg_report,
        import_tjg_report_from_token,
        import_tjg_report_from_url,
    )

    body: dict | None = None
    try:
        body = await request.json()
    except Exception:
        body = None

    if isinstance(body, dict) and body.get("data"):
        result = await import_tjg_report(
            db,
            body,
            token=str(body.get("token") or token or ""),
            replace_existing=replace_existing,
        )
    elif share_url:
        result = await import_tjg_report_from_url(db, share_url, replace_existing=replace_existing)
    elif token:
        result = await import_tjg_report_from_token(db, token, replace_existing=replace_existing)
    else:
        raise HTTPException(status_code=400, detail="token_share_url_or_payload_required")

    return success(request, result, status=201)


@router.get("/strategy/reports/{report_id}")
async def strategy_report_detail(report_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.report_composer import get_visibility_report_detail

    return success(request, await get_visibility_report_detail(db, report_id))


@router.get("/strategy/monitor/competitor-matrix")
async def strategy_monitor_competitor_matrix(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.competitive_analyzer import build_competitor_matrix

    return success(request, await build_competitor_matrix(db))


@router.get("/strategy/monitor/settings")
async def strategy_monitor_settings_get(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_monitor_settings(db))


@router.patch("/strategy/monitor/settings")
async def strategy_monitor_settings_patch(
    body: MonitorSettingsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await save_monitor_settings(db, body))


@router.get("/strategy/monitor/runs")
async def strategy_monitor_runs_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_monitor_runs(db))


@router.get("/strategy/monitor/runs/{run_id}")
async def strategy_monitor_run_detail(
    run_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await build_monitor_run_detail(db, run_id))


@router.get("/strategy/geo-eval")
async def strategy_geo_eval(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await build_geo_eval_panel(db))


@router.get("/strategy/geo-eval/articles/{article_id}")
async def strategy_geo_eval_article_detail(
    article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    """GeoEval 单篇评估明细（Wave E drill-down）。"""
    from app.models.geoeval import ArticleEvaluation

    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    rows = (
        await db.execute(
            select(ArticleEvaluation)
            .where(ArticleEvaluation.article_id == article_id)
            .order_by(ArticleEvaluation.id.desc())
            .limit(10)
        )
    ).scalars().all()
    evals = [
        {
            "id": int(e.id),
            "status": e.status,
            "eval_type": e.eval_type,
            "metrics": e.metrics or {},
            "simulation_score": (e.metrics or {}).get("simulation_score") if isinstance(e.metrics, dict) else None,
            "audit_score": (e.metrics or {}).get("audit_score") if isinstance(e.metrics, dict) else None,
            "failure_reason": e.failure_reason,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]
    logger = logging.getLogger(__name__)
    logger.info("geo_eval_article_detail article_id=%s evals=%s", article_id, len(evals))
    return success(
        request,
        {
            "article": {
                "id": article.id,
                "title": article.title,
                "status": article.status,
                "eval_meta": article.eval_meta or {},
            },
            "evaluations": evals,
        },
    )


class SalesCopyBody(BaseModel):
    title: str
    body: str
    copy_type: str = "talking_point"
    scene_id: int | None = None
    tech_ip_asset_id: int | None = None
    meta: dict | None = None
    id: int | None = None


@router.get("/strategy/sales-copy")
async def strategy_sales_copy_list(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    scene_id: int | None = None,
    copy_type: str | None = None,
):
    from app.services.geoeval.sales_copy_service import list_sales_copy

    return success(request, await list_sales_copy(db, scene_id=scene_id, copy_type=copy_type))


@router.post("/strategy/sales-copy")
async def strategy_sales_copy_upsert(body: SalesCopyBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.sales_copy_service import upsert_sales_copy

    return success(
        request,
        await upsert_sales_copy(
            db,
            title=body.title,
            body=body.body,
            copy_type=body.copy_type,
            scene_id=body.scene_id,
            tech_ip_asset_id=body.tech_ip_asset_id,
            meta=body.meta,
            asset_id=body.id,
        ),
        status=201,
    )


@router.put("/strategy/geo-eval/settings")
async def strategy_geo_eval_settings_put(
    body: GeoEvalSettingsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    return success(request, await save_geo_eval_settings(db, body))


@router.post("/strategy/geo-eval/reevaluate/{article_id}")
async def strategy_reevaluate_article(article_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.evaluate_article", args=[article_id])
    return success(request, {"queued": True, "article_id": article_id})


class GeoEvalSimulateBody(BaseModel):
    title: str = Field(default="", max_length=300)
    content: str = Field(default="", max_length=50000)
    query: str | None = Field(default=None, max_length=200)
    keyword: str | None = Field(default=None, max_length=200)
    kb_id: int | None = None
    article_id: int | None = None

    def require_payload(self) -> None:
        if self.article_id:
            return
        if not (self.title or "").strip() or not (self.content or "").strip():
            raise HTTPException(status_code=400, detail="title_and_content_required")


@router.post("/strategy/geo-eval/simulate")
async def strategy_geo_eval_simulate(
    body: GeoEvalSimulateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)
):
    """虚拟 GEO 环境仿真：返回内容被 AI 检索/采纳的概率拆解（不落库）。"""
    from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config
    from app.services.geoeval.eval_context import load_default_kb_id, resolve_eval_model, resolve_kb_id
    from app.services.geoeval.simulation_rag import SimulationRagService

    body.require_payload()
    gate = await get_geo_eval_gate_config(db)
    pass_score = float(gate.get("simulation_pass_score") or 0.55)
    model = None
    kb_id = body.kb_id
    title = body.title
    content = body.content
    keyword = body.keyword

    if body.article_id:
        article = await db.get(Article, body.article_id)
        if article is None or article.deleted_at:
            raise HTTPException(status_code=404, detail="article_not_found")
        title = article.title or title
        content = article.content or content
        keyword = keyword or article.original_keyword or article.keywords
        kb_id = kb_id or await resolve_kb_id(db, article)
        model = await resolve_eval_model(db, article)
    else:
        kb_id = kb_id or await load_default_kb_id(db)
        from app.services.geoflow.llm_client import get_active_chat_model

        model = await get_active_chat_model(db)

    if not (title or "").strip() or not (content or "").strip():
        raise HTTPException(status_code=400, detail="title_and_content_required")

    sim = await SimulationRagService(db).simulate_draft(
        title=title,
        content=content,
        query=body.query,
        keyword=keyword,
        kb_id=kb_id,
        model=model,
    )
    adoption = float(sim.get("adoption_probability") or sim.get("simulation_score") or 0)
    payload = {
        **sim,
        "pass_threshold": pass_score,
        "passes_threshold": adoption >= pass_score,
        "probability_pct": round(adoption * 100, 1),
        "breakdown": {
            "retrieval": float(sim.get("retrieval_probability") or sim.get("retrieval_score") or 0),
            "overlap": float(sim.get("overlap_score") or 0),
            "confidence": float(sim.get("confidence") or 0),
            "in_context": float(sim.get("in_context_probability") or 0),
            "adoption": adoption,
        },
    }
    logging.getLogger(__name__).info(
        "geo_eval_simulate_api article_id=%s score=%s pass=%s",
        body.article_id,
        adoption,
        payload["passes_threshold"],
    )
    return success(request, payload)


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


@router.post("/tech-assets/import-yaml")
async def import_tech_assets(body: TechYamlImportBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await import_tech_assets_yaml(db, body))


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
    result = await create_knowledge_base(db, body)
    kb_id = result["item"]["id"]
    await db.commit()
    result["sync_queued"] = queue_knowledge_chunk_sync(kb_id)
    return success(request, result, status=201)


@router.patch("/knowledge-bases/{kb_id}")
async def knowledge_base_update(kb_id: int, body: KnowledgeBaseBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    result = await update_knowledge_base(db, kb_id, body)
    await db.commit()
    result["sync_queued"] = queue_knowledge_chunk_sync(kb_id)
    return success(request, result)


@router.delete("/knowledge-bases/{kb_id}")
async def knowledge_base_delete(kb_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_knowledge_base(db, kb_id))


@router.post("/knowledge-bases/{kb_id}/upload-file")
async def knowledge_base_upload_file(
    kb_id: int,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    file: UploadFile = File(...),
):
    parsed = await read_knowledge_upload(file)
    result = await append_knowledge_file_content(db, kb_id, parsed["content"], parsed["filename"])
    await db.commit()
    result["sync_queued"] = queue_knowledge_chunk_sync(kb_id)
    return success(request, result)


@router.get("/knowledge-settings")
async def knowledge_settings_get(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_knowledge_settings(db))


@router.patch("/knowledge-settings")
async def knowledge_settings_patch(body: KnowledgeSettingsBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await save_knowledge_settings(db, body))


@router.post("/knowledge-bases/rag-sandbox")
async def knowledge_rag_sandbox(body: RagSandboxBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await run_rag_sandbox(db, body))


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


@router.get("/agents")
async def agents_list(request: Request, jwt=Depends(get_admin_jwt)):
    return success(request, list_agents())


@router.get("/agents/{agent_id}")
async def agents_get(agent_id: str, request: Request, jwt=Depends(get_admin_jwt)):
    return success(request, get_agent_config(agent_id))


@router.patch("/agents/{agent_id}")
async def agents_update(agent_id: str, body: AgentUpdateBody, request: Request, jwt=Depends(get_admin_jwt)):
    return success(request, update_agent_config(agent_id, body))


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


@router.post("/materials/title-libraries/{library_id}/titles/bulk")
async def titles_bulk(library_id: int, body: BulkTitlesBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await bulk_create_titles(db, library_id, body), status=201)


@router.post("/materials/title-libraries/{library_id}/titles/generate")
async def titles_generate(library_id: int, body: TitleGenerateBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await generate_titles(db, library_id, body))


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


@router.delete("/materials/keyword-libraries/{library_id}")
async def keyword_libraries_delete(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_keyword_library(db, library_id))


@router.delete("/materials/keywords/{keyword_id}")
async def keywords_delete(keyword_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_keyword(db, keyword_id))


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


@router.post("/materials/image-libraries/{library_id}/images/upload")
async def images_upload(
    library_id: int,
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    file: UploadFile = File(...),
):
    from app.services.admin.materials_libraries_service import ImageMetaBody, create_image_meta

    meta = await save_image_upload(library_id, file)
    item = await create_image_meta(
        db,
        library_id,
        ImageMetaBody(
            original_name=meta["original_name"],
            file_path=meta["file_path"],
            mime_type=meta["mime_type"],
            file_size=meta["file_size"],
        ),
    )
    return success(request, item, status=201)


@router.delete("/materials/image-libraries/{library_id}")
async def image_libraries_delete(library_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_image_library(db, library_id))


@router.delete("/materials/images/{image_id}")
async def images_delete(image_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await delete_image(db, image_id))


@router.post("/production/url-import")
async def url_import_run(body: UrlImportBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await run_url_import(db, body), status=201)


@router.get("/production/url-import/history")
async def url_import_history(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await list_url_import_history(db))


@router.get("/production/url-import/{job_id}")
async def url_import_show(job_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await get_url_import_job(db, job_id))


@router.post("/production/url-import/{job_id}/commit")
async def url_import_commit(job_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await commit_url_import_job(db, job_id))


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


@router.get("/strategy/monitor/questions")
async def monitor_questions_list(
    request: Request,
    db: DbSession,
    jwt=Depends(get_admin_jwt),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query_type: str | None = Query(default=None, pattern="^(brand|product|competitor)$"),
    status: str | None = Query(default=None, pattern="^(active|paused)$"),
    scene_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, max_length=200),
):
    return success(
        request,
        await list_monitor_questions(
            db,
            page=page,
            page_size=page_size,
            query_type=query_type,
            status=status,
            scene_id=scene_id,
            search=search,
        ),
    )


@router.post("/strategy/monitor/questions/bulk")
async def monitor_questions_bulk(body: MonitorQuestionBulkBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await bulk_import_monitor_questions(db, body), status=201)


@router.post("/strategy/monitor/questions/seed-brand")
async def monitor_questions_seed_brand(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    return success(request, await seed_default_brand_questions(db), status=201)


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


class GoldLabelBody(BaseModel):
    question_id: int | None = None
    platform: str
    source: str = "manual"
    mentioned: bool = False
    brand_rank: int | None = None
    snippet: str = ""
    cited_urls: list[str] | None = None
    open_api_probe_id: int | None = None
    notes: str = ""
    captured_at: str | None = None


class GoldJsonlBody(BaseModel):
    content: str = Field(min_length=1, description="JSONL 文本，每行一条金标")


@router.get("/strategy/gold-labels")
async def strategy_gold_labels_list(request: Request, db: DbSession, jwt=Depends(get_admin_jwt), limit: int = Query(100, ge=1, le=500)):
    from app.services.geoeval.gold_bias_service import list_gold_labels

    return success(request, await list_gold_labels(db, limit=limit))


@router.post("/strategy/gold-labels")
async def strategy_gold_labels_create(body: GoldLabelBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.gold_bias_service import upsert_gold_label

    try:
        return success(request, await upsert_gold_label(db, body.model_dump()), status=201)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/strategy/gold-labels/import-jsonl")
async def strategy_gold_labels_import(body: GoldJsonlBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.services.geoeval.gold_bias_service import import_gold_jsonl

    lines = body.content.splitlines()
    return success(request, await import_gold_jsonl(db, lines), status=201)


@router.get("/strategy/gold-labels/bias")
async def strategy_gold_bias(request: Request, db: DbSession, jwt=Depends(get_admin_jwt), days: int = Query(30, ge=1, le=365)):
    from app.services.geoeval.gold_bias_service import compute_gold_bias

    return success(request, await compute_gold_bias(db, days=days))


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
