from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.response import success
from app.models.article import Article
from app.services.geoflow.article_publish import ArticlePublishService

router = APIRouter()


class ArticleCreate(BaseModel):
    title: str
    slug: str
    content: str
    category_id: int
    author_id: int
    task_id: int | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    review_status: str | None = None


@router.get("/articles")
async def list_articles(request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:read")
    rows = (
        await db.execute(select(Article).where(Article.deleted_at.is_(None)).order_by(Article.id.desc()).limit(100))
    ).scalars().all()
    return success(request, {"articles": [_article_dict(a) for a in rows]})


@router.post("/articles")
async def create_article(body: ArticleCreate, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:write")
    article = Article(
        title=body.title,
        slug=body.slug,
        content=body.content,
        category_id=body.category_id,
        author_id=body.author_id,
        task_id=body.task_id,
        is_ai_generated=1 if body.task_id else 0,
    )
    db.add(article)
    await db.flush()
    return success(request, {"article": _article_dict(article)}, status=201)


@router.get("/articles/{article_id}")
async def show_article(article_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:read")
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    return success(request, {"article": _article_dict(article, full=True)})


@router.patch("/articles/{article_id}")
async def update_article(
    article_id: int, body: ArticleUpdate, request: Request, db: DbSession, auth=Depends(get_api_auth)
):
    _, scopes = auth
    require_scope(scopes, "articles:write")
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    if body.title is not None:
        article.title = body.title
    if body.content is not None:
        article.content = body.content
    if body.review_status is not None:
        article.review_status = body.review_status
    return success(request, {"article": _article_dict(article)})


@router.post("/articles/{article_id}/review")
async def review_article(article_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:write")
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    article.review_status = "approved"
    return success(request, {"article": _article_dict(article)})


@router.post("/articles/{article_id}/publish")
async def publish_article(article_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:publish")
    svc = ArticlePublishService(db)
    article = await svc.publish(article_id)
    return success(request, {"article": _article_dict(article)})


@router.post("/articles/{article_id}/trash")
async def trash_article(article_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "articles:write")
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    article.deleted_at = datetime.now(UTC)
    article.status = "trashed"
    return success(request, {"article": _article_dict(article)})


def _article_dict(article: Article, full: bool = False) -> dict:
    data = {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "status": article.status,
        "review_status": article.review_status,
        "eval_status": article.eval_status,
        "content_format": article.content_format,
        "task_id": article.task_id,
        "published_at": article.published_at.isoformat() if article.published_at else None,
    }
    if full:
        data["content"] = article.content
        data["wiki_meta"] = article.wiki_meta
    return data
