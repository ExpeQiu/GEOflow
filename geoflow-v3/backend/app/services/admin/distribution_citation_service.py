"""分发内容 ↔ AI 探针引用归因 — 识别已分发文章是否被索引引用。"""

import json
import logging
import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.services.admin.production_service import _table_exists
from app.services.geoeval.citation_chain_service import PLATFORM_LABELS, _domain
from app.services.geoeval.monitor_probe import aggregate_probe_kpis

logger = logging.getLogger(__name__)

SYNCED_STATUSES = ("synced", "published")
TITLE_MATCH_THRESHOLD = 0.85
ALERT_TYPE_NOT_INDEXED = "distribution_not_indexed"
ALERT_TYPE_INDEX_DROP = "distribution_index_drop"


def _normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower().replace("www.", "")
        path = (parsed.path or "").rstrip("/").lower()
        return f"{host}{path}"
    except Exception:
        return raw.lower().rstrip("/")


def _title_similarity(a: str, b: str) -> float:
    left = re.sub(r"\s+", "", (a or "").lower())
    right = re.sub(r"\s+", "", (b or "").lower())
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _match_urls(article_urls: list[str], citation_url: str) -> tuple[bool, str]:
    cite_norm = _normalize_url(citation_url)
    if not cite_norm:
        return False, ""
    for article_url in article_urls:
        art_norm = _normalize_url(article_url)
        if not art_norm:
            continue
        if art_norm == cite_norm:
            return True, "exact"
        if art_norm in cite_norm or cite_norm in art_norm:
            return True, "path"
    return False, ""


def _resolve_index_status(*, synced: bool, citation_count: int, has_probe_data: bool) -> str:
    if not synced:
        return "not_distributed"
    if citation_count > 0:
        return "indexed"
    if has_probe_data:
        return "not_indexed"
    return "pending_scan"


async def _has_probe_data(db: AsyncSession) -> bool:
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return False
    count = int(await db.scalar(text("SELECT COUNT(*) FROM geo_monitor_probe_results LIMIT 1")) or 0)
    return count > 0


async def _cache_tables_ready(db: AsyncSession) -> bool:
    return await _table_exists(db, "distribution_citation_index") and await _table_exists(
        db, "distribution_citation_snapshots"
    )


async def _load_distributed_rows(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(ArticleDistribution, Article, DistributionChannel)
            .join(Article, Article.id == ArticleDistribution.article_id)
            .join(DistributionChannel, DistributionChannel.id == ArticleDistribution.channel_id)
            .where(ArticleDistribution.status.in_(SYNCED_STATUSES), Article.deleted_at.is_(None))
            .order_by(ArticleDistribution.updated_at.desc(), ArticleDistribution.id.desc())
        )
    ).all()

    grouped: dict[int, dict] = {}
    for dist, article, channel in rows:
        bucket = grouped.get(article.id)
        if bucket is None:
            bucket = {
                "article_id": article.id,
                "title": article.title,
                "slug": article.slug,
                "distributions": [],
                "article_urls": [],
            }
            grouped[article.id] = bucket
        remote_url = (dist.remote_url or "").strip()
        bucket["distributions"].append(
            {
                "distribution_id": dist.id,
                "channel_id": channel.id,
                "channel_name": channel.name,
                "channel_type": channel.channel_type,
                "remote_url": remote_url or None,
                "synced_at": dist.updated_at.isoformat() if dist.updated_at else None,
            }
        )
        if remote_url:
            bucket["article_urls"].append(remote_url)

    return list(grouped.values())


async def _load_citation_records(db: AsyncSession, *, since_days: int | None = None) -> list[dict]:
    if not await _table_exists(db, "geo_monitor_probe_citations"):
        return []
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return []

    has_questions = await _table_exists(db, "geo_monitor_questions")
    join_question = "LEFT JOIN geo_monitor_questions mq ON mq.id = pr.question_id" if has_questions else ""
    select_question = (
        "mq.id AS question_id, mq.question_text, mq.scene_id"
        if has_questions
        else "NULL AS question_id, NULL AS question_text, NULL AS scene_id"
    )
    time_filter = ""
    params: dict = {}
    if since_days is not None and since_days > 0:
        time_filter = "AND pr.created_at >= CURRENT_TIMESTAMP - (:days * INTERVAL '1 day')"
        params["days"] = since_days

    rows = (
        await db.execute(
            text(
                f"""
                SELECT pc.id, pc.title, pc.url, pc.position,
                       pr.platform, {select_question}
                FROM geo_monitor_probe_citations pc
                JOIN geo_monitor_probe_results pr ON pr.id = pc.probe_result_id
                {join_question}
                WHERE 1=1 {time_filter}
                ORDER BY pc.id DESC
                """
            ),
            params,
        )
    ).all()

    records: list[dict] = []
    for row in rows:
        cid, title, url, position, platform = row[0], row[1], row[2], row[3], row[4]
        question_id = row[5] if len(row) > 5 else None
        question_text = row[6] if len(row) > 6 else None
        scene_id = row[7] if len(row) > 7 else None
        records.append(
            {
                "id": int(cid),
                "title": str(title or ""),
                "url": str(url or ""),
                "position": int(position or 0),
                "domain": _domain(str(url or "")),
                "platform": str(platform or ""),
                "platform_label": PLATFORM_LABELS.get(str(platform or ""), str(platform or "")),
                "question_id": int(question_id) if question_id is not None else None,
                "question_text": str(question_text or ""),
                "scene_id": int(scene_id) if scene_id is not None else None,
            }
        )
    return records


def _match_article_citations(article: dict, citations: list[dict], *, has_probe_data: bool) -> dict:
    article_urls = list(dict.fromkeys(article.get("article_urls") or []))
    title = str(article.get("title") or "")
    matched: list[dict] = []
    question_ids: set[int] = set()
    platforms: set[str] = set()
    match_types: set[str] = set()

    for cite in citations:
        ok, match_type = _match_urls(article_urls, cite["url"])
        if not ok and title and cite.get("title"):
            if _title_similarity(title, cite["title"]) >= TITLE_MATCH_THRESHOLD:
                ok, match_type = True, "title"
        if not ok:
            continue
        matched.append({**cite, "match_type": match_type})
        match_types.add(match_type)
        if cite.get("question_id"):
            question_ids.add(int(cite["question_id"]))
        if cite.get("platform"):
            platforms.add(str(cite["platform"]))

    citation_count = len(matched)
    index_status = _resolve_index_status(
        synced=True,
        citation_count=citation_count,
        has_probe_data=has_probe_data,
    )
    primary_url = article_urls[0] if article_urls else None
    sorted_platforms = sorted(platforms)

    return {
        "article_id": article["article_id"],
        "title": title,
        "primary_url": primary_url,
        "distributions": article.get("distributions") or [],
        "index_status": index_status,
        "citation_count": citation_count,
        "scene_question_count": len(question_ids),
        "platforms": sorted_platforms,
        "platform_labels": [PLATFORM_LABELS.get(p, p) for p in sorted_platforms],
        "match_types": sorted(match_types),
        "citations": matched[:50],
    }


async def _compute_all_article_rows(db: AsyncSession) -> tuple[list[dict], list[dict], bool]:
    distributed = await _load_distributed_rows(db)
    citations = await _load_citation_records(db)
    has_probe_data = bool(citations) or await _has_probe_data(db)
    rows = [_match_article_citations(item, citations, has_probe_data=has_probe_data) for item in distributed]
    return rows, citations, has_probe_data


def _summarize_rows(article_rows: list[dict], citations: list[dict], kpis: dict, question_count: int) -> dict:
    indexed_count = sum(1 for row in article_rows if row["index_status"] == "indexed")
    not_indexed_count = sum(1 for row in article_rows if row["index_status"] == "not_indexed")
    pending_scan_count = sum(1 for row in article_rows if row["index_status"] == "pending_scan")
    positive_rate = kpis.get("sentiment_score")

    return {
        "distributed_count": len(article_rows),
        "indexed_count": indexed_count,
        "not_indexed_count": not_indexed_count,
        "pending_scan_count": pending_scan_count,
        "citation_source_count": len(citations),
        "visibility_pct": float(kpis.get("visibility_pct") or 0),
        "positive_rate_pct": float(positive_rate) if positive_rate is not None else None,
        "monitored_questions": question_count,
        "article_cited_count": indexed_count,
    }


async def _create_distribution_alert(db: AsyncSession, alert_type: str, message: str, payload: dict) -> None:
    if not await _table_exists(db, "geo_admin_alerts"):
        logger.warning("geo_admin_alerts_table_missing")
        return
    await db.execute(
        text(
            "INSERT INTO geo_admin_alerts (alert_type, message, payload_json) VALUES (:t, :m, CAST(:p AS JSON))"
        ),
        {"t": alert_type, "m": message, "p": json.dumps(payload, ensure_ascii=False)},
    )
    logger.info("distribution_citation_alert_created type=%s", alert_type)


async def check_distribution_citation_alerts(db: AsyncSession, summary: dict) -> dict:
    created = 0
    not_indexed = int(summary.get("not_indexed_count") or 0)
    distributed = int(summary.get("distributed_count") or 0)

    if not_indexed > 0 and distributed > 0:
        await _create_distribution_alert(
            db,
            ALERT_TYPE_NOT_INDEXED,
            f"{not_indexed} 篇已分发文章尚未被 AI 引用索引（共 {distributed} 篇）",
            {
                "not_indexed_count": not_indexed,
                "distributed_count": distributed,
                "articles": summary.get("not_indexed_preview") or [],
            },
        )
        created += 1

    if await _cache_tables_ready(db):
        week_ago = date.today() - timedelta(days=7)
        old_row = (
            await db.execute(
                text(
                    """
                    SELECT indexed_count FROM distribution_citation_snapshots
                    WHERE snapshot_date <= :d
                    ORDER BY snapshot_date DESC
                    LIMIT 1
                    """
                ),
                {"d": week_ago},
            )
        ).first()
        if old_row is not None:
            old_indexed = int(old_row[0] or 0)
            current_indexed = int(summary.get("indexed_count") or 0)
            if old_indexed > 0 and current_indexed < old_indexed:
                drop = old_indexed - current_indexed
                await _create_distribution_alert(
                    db,
                    ALERT_TYPE_INDEX_DROP,
                    f"被引用文章数 7 日下降 {drop} 篇（{old_indexed} → {current_indexed}）",
                    {"old_indexed": old_indexed, "current_indexed": current_indexed, "drop": drop},
                )
                created += 1

    return {"alerts_created": created}


async def refresh_distribution_citation_cache(db: AsyncSession) -> dict:
    article_rows, citations, has_probe_data = await _compute_all_article_rows(db)
    kpis = await aggregate_probe_kpis(db)
    question_count = 0
    if await _table_exists(db, "geo_monitor_questions"):
        question_count = int(
            await db.scalar(text("SELECT COUNT(*) FROM geo_monitor_questions WHERE status = 'active'")) or 0
        )

    summary = _summarize_rows(article_rows, citations, kpis, question_count)
    not_indexed_preview = [
        {"article_id": r["article_id"], "title": r["title"], "primary_url": r.get("primary_url")}
        for r in article_rows
        if r["index_status"] == "not_indexed"
    ][:8]
    summary["not_indexed_preview"] = not_indexed_preview

    if await _cache_tables_ready(db):
        current_ids = [row["article_id"] for row in article_rows]
        if current_ids:
            await db.execute(
                text(
                    f"""
                    DELETE FROM distribution_citation_index
                    WHERE article_id NOT IN ({",".join(str(i) for i in current_ids)})
                    """
                )
            )
        else:
            await db.execute(text("DELETE FROM distribution_citation_index"))

        for row in article_rows:
            await db.execute(
                text(
                    """
                    INSERT INTO distribution_citation_index
                        (article_id, index_status, citation_count, scene_question_count,
                         primary_url, platforms_json, match_types_json, citations_json,
                         distributions_json, last_matched_at, updated_at)
                    VALUES
                        (:aid, :status, :cc, :sq, :url,
                         CAST(:platforms AS JSON), CAST(:match_types AS JSON),
                         CAST(:citations AS JSON), CAST(:distributions AS JSON),
                         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (article_id) DO UPDATE SET
                        index_status = EXCLUDED.index_status,
                        citation_count = EXCLUDED.citation_count,
                        scene_question_count = EXCLUDED.scene_question_count,
                        primary_url = EXCLUDED.primary_url,
                        platforms_json = EXCLUDED.platforms_json,
                        match_types_json = EXCLUDED.match_types_json,
                        citations_json = EXCLUDED.citations_json,
                        distributions_json = EXCLUDED.distributions_json,
                        last_matched_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "aid": row["article_id"],
                    "status": row["index_status"],
                    "cc": row["citation_count"],
                    "sq": row["scene_question_count"],
                    "url": row.get("primary_url"),
                    "platforms": json.dumps(row.get("platforms") or []),
                    "match_types": json.dumps(row.get("match_types") or []),
                    "citations": json.dumps(row.get("citations") or []),
                    "distributions": json.dumps(row.get("distributions") or []),
                },
            )

        today = date.today()
        await db.execute(
            text(
                """
                INSERT INTO distribution_citation_snapshots
                    (snapshot_date, distributed_count, indexed_count, not_indexed_count,
                     pending_scan_count, citation_source_count, visibility_pct,
                     positive_rate_pct, monitored_questions)
                VALUES
                    (:d, :dc, :ic, :nic, :psc, :csc, :vp, :pr, :mq)
                ON CONFLICT (snapshot_date) DO UPDATE SET
                    distributed_count = EXCLUDED.distributed_count,
                    indexed_count = EXCLUDED.indexed_count,
                    not_indexed_count = EXCLUDED.not_indexed_count,
                    pending_scan_count = EXCLUDED.pending_scan_count,
                    citation_source_count = EXCLUDED.citation_source_count,
                    visibility_pct = EXCLUDED.visibility_pct,
                    positive_rate_pct = EXCLUDED.positive_rate_pct,
                    monitored_questions = EXCLUDED.monitored_questions
                """
            ),
            {
                "d": today,
                "dc": summary["distributed_count"],
                "ic": summary["indexed_count"],
                "nic": summary["not_indexed_count"],
                "psc": summary["pending_scan_count"],
                "csc": summary["citation_source_count"],
                "vp": summary["visibility_pct"],
                "pr": summary["positive_rate_pct"],
                "mq": summary["monitored_questions"],
            },
        )

    alerts = await check_distribution_citation_alerts(db, summary)
    logger.info(
        "distribution_citation_cache_refreshed distributed=%s indexed=%s not_indexed=%s alerts=%s",
        summary["distributed_count"],
        summary["indexed_count"],
        summary["not_indexed_count"],
        alerts.get("alerts_created", 0),
    )
    return {
        "status": "ok",
        "refreshed_at": date.today().isoformat(),
        **summary,
        **alerts,
    }


async def _load_cached_article_rows(db: AsyncSession) -> list[dict] | None:
    if not await _cache_tables_ready(db):
        return None
    count = int(await db.scalar(text("SELECT COUNT(*) FROM distribution_citation_index")) or 0)
    if count == 0:
        return None

    rows = (
        await db.execute(
            text(
                """
                SELECT i.article_id, a.title, i.primary_url, i.index_status, i.citation_count,
                       i.scene_question_count, i.platforms_json, i.match_types_json,
                       i.citations_json, i.distributions_json, i.last_matched_at
                FROM distribution_citation_index i
                JOIN articles a ON a.id = i.article_id
                WHERE a.deleted_at IS NULL
                ORDER BY i.citation_count DESC, i.updated_at DESC
                """
            )
        )
    ).all()

    result: list[dict] = []
    for row in rows:
        platforms = row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]")
        citations = row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]")
        distributions = row[9] if isinstance(row[9], list) else json.loads(row[9] or "[]")
        match_types = row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]")
        result.append(
            {
                "article_id": int(row[0]),
                "title": str(row[1]),
                "primary_url": row[2],
                "index_status": str(row[3]),
                "citation_count": int(row[4] or 0),
                "scene_question_count": int(row[5] or 0),
                "platforms": platforms,
                "platform_labels": [PLATFORM_LABELS.get(p, p) for p in platforms],
                "match_types": match_types,
                "citations": citations,
                "distributions": distributions,
                "last_matched_at": row[10].isoformat() if row[10] else None,
            }
        )
    return result


async def _load_snapshot_for_date(db: AsyncSession, target: date) -> dict | None:
    if not await _cache_tables_ready(db):
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT distributed_count, indexed_count, not_indexed_count, pending_scan_count,
                       citation_source_count, visibility_pct, positive_rate_pct, monitored_questions
                FROM distribution_citation_snapshots
                WHERE snapshot_date <= :d
                ORDER BY snapshot_date DESC
                LIMIT 1
                """
            ),
            {"d": target},
        )
    ).first()
    if not row:
        return None
    return {
        "distributed_count": int(row[0] or 0),
        "indexed_count": int(row[1] or 0),
        "not_indexed_count": int(row[2] or 0),
        "pending_scan_count": int(row[3] or 0),
        "citation_source_count": int(row[4] or 0),
        "visibility_pct": float(row[5] or 0),
        "positive_rate_pct": float(row[6]) if row[6] is not None else None,
        "monitored_questions": int(row[7] or 0),
        "article_cited_count": int(row[1] or 0),
    }


def _calc_delta(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(float(current) - float(previous), 1)


def _build_kpi_deltas(current: dict, previous: dict | None) -> dict:
    if not previous:
        return {}
    negative_current = (
        round(100 - float(current["positive_rate_pct"]), 1)
        if current.get("positive_rate_pct") is not None
        else None
    )
    negative_previous = (
        round(100 - float(previous["positive_rate_pct"]), 1)
        if previous.get("positive_rate_pct") is not None
        else None
    )
    return {
        "monitored_questions": _calc_delta(current.get("monitored_questions"), previous.get("monitored_questions")),
        "visibility_pct": _calc_delta(current.get("visibility_pct"), previous.get("visibility_pct")),
        "citation_source_count": _calc_delta(current.get("citation_source_count"), previous.get("citation_source_count")),
        "article_cited_count": _calc_delta(current.get("article_cited_count"), previous.get("article_cited_count")),
        "positive_rate_pct": _calc_delta(current.get("positive_rate_pct"), previous.get("positive_rate_pct")),
        "negative_rate_pct": _calc_delta(negative_current, negative_previous),
    }


async def _get_last_refreshed_at(db: AsyncSession) -> str | None:
    if not await _cache_tables_ready(db):
        return None
    row = await db.scalar(text("SELECT MAX(last_matched_at) FROM distribution_citation_index"))
    return row.isoformat() if row else None


async def build_distribution_citation_summary(db: AsyncSession) -> dict:
    cached = await _load_cached_article_rows(db)
    if cached:
        indexed = sum(1 for r in cached if r["index_status"] == "indexed")
        not_indexed = sum(1 for r in cached if r["index_status"] == "not_indexed")
        return {
            "distributed_count": len(cached),
            "indexed_count": indexed,
            "not_indexed_count": not_indexed,
            "last_refreshed_at": await _get_last_refreshed_at(db),
        }
    article_rows, _, _ = await _compute_all_article_rows(db)
    return {
        "distributed_count": len(article_rows),
        "indexed_count": sum(1 for r in article_rows if r["index_status"] == "indexed"),
        "not_indexed_count": sum(1 for r in article_rows if r["index_status"] == "not_indexed"),
        "last_refreshed_at": None,
    }


async def build_distribution_citation_overview(db: AsyncSession, *, days: int = 7) -> dict:
    cached_rows = await _load_cached_article_rows(db)
    citations = await _load_citation_records(db)
    has_probe_data = bool(citations) or await _has_probe_data(db)

    if cached_rows is not None:
        article_rows = cached_rows
    else:
        distributed = await _load_distributed_rows(db)
        article_rows = [
            _match_article_citations(item, citations, has_probe_data=has_probe_data) for item in distributed
        ]

    kpis_probe = await aggregate_probe_kpis(db)
    question_count = 0
    if await _table_exists(db, "geo_monitor_questions"):
        question_count = int(
            await db.scalar(text("SELECT COUNT(*) FROM geo_monitor_questions WHERE status = 'active'")) or 0
        )

    current_summary = _summarize_rows(article_rows, citations, kpis_probe, question_count)
    week_ago_summary = await _load_snapshot_for_date(db, date.today() - timedelta(days=days))
    kpi_deltas = _build_kpi_deltas(current_summary, week_ago_summary)

    domain_counts: dict[str, int] = {}
    for cite in citations:
        domain = cite.get("domain") or "unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    top_domains = sorted(domain_counts.items(), key=lambda x: (-x[1], x[0]))[:12]

    positive_rate = current_summary.get("positive_rate_pct")
    negative_rate = round(100 - positive_rate, 1) if positive_rate is not None else None
    platform_set = {p for row in article_rows for p in row.get("platforms") or []}

    alerts: list[dict] = []
    if current_summary["not_indexed_count"] > 0:
        alerts.append(
            {
                "type": ALERT_TYPE_NOT_INDEXED,
                "severity": "warning",
                "message": f"{current_summary['not_indexed_count']} 篇已分发文章尚未被 AI 引用索引",
                "count": current_summary["not_indexed_count"],
            }
        )

    logger.info(
        "distribution_citation_overview distributed=%s indexed=%s citations=%s days=%s cached=%s",
        current_summary["distributed_count"],
        current_summary["indexed_count"],
        len(citations),
        days,
        cached_rows is not None,
    )
    return {
        "period_days": days,
        "has_probe_data": has_probe_data,
        "cache_ready": cached_rows is not None,
        "last_refreshed_at": await _get_last_refreshed_at(db),
        "kpis": {
            "monitored_questions": current_summary["monitored_questions"],
            "visibility_pct": current_summary["visibility_pct"],
            "citation_source_count": current_summary["citation_source_count"],
            "article_cited_count": current_summary["article_cited_count"],
            "distributed_article_count": current_summary["distributed_count"],
            "not_indexed_count": current_summary["not_indexed_count"],
            "positive_rate_pct": positive_rate,
            "negative_rate_pct": negative_rate,
        },
        "kpis_delta": kpi_deltas,
        "alerts": alerts,
        "contribution": {
            "cited_articles": current_summary["indexed_count"],
            "citation_sources": current_summary["citation_source_count"],
            "platform_coverage": len(platform_set),
        },
        "domain_chart": [{"domain": d, "count": c} for d, c in top_domains],
        "articles_preview": article_rows[:10],
    }


async def build_distributed_article_citations(
    db: AsyncSession,
    *,
    status: str = "all",
    page: int = 1,
    per_page: int = 50,
) -> dict:
    cached_rows = await _load_cached_article_rows(db)
    if cached_rows is not None:
        all_rows = cached_rows
    else:
        distributed = await _load_distributed_rows(db)
        citations = await _load_citation_records(db)
        has_probe_data = bool(citations) or await _has_probe_data(db)
        all_rows = [
            _match_article_citations(item, citations, has_probe_data=has_probe_data) for item in distributed
        ]

    rows = all_rows
    if status == "indexed":
        rows = [r for r in rows if r["index_status"] == "indexed"]
    elif status == "not_indexed":
        rows = [r for r in rows if r["index_status"] == "not_indexed"]
    elif status == "pending_scan":
        rows = [r for r in rows if r["index_status"] == "pending_scan"]

    total = len(rows)
    start = max(0, (page - 1) * per_page)
    end = start + per_page

    logger.info("distribution_citation_articles status=%s total=%s page=%s cached=%s", status, total, page, cached_rows is not None)
    return {
        "articles": rows[start:end],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
        "stats": {
            "total": len(all_rows),
            "indexed": sum(1 for r in all_rows if r["index_status"] == "indexed"),
            "not_indexed": sum(1 for r in all_rows if r["index_status"] == "not_indexed"),
            "pending_scan": sum(1 for r in all_rows if r["index_status"] == "pending_scan"),
        },
        "last_refreshed_at": await _get_last_refreshed_at(db),
    }


async def build_article_citation_detail(db: AsyncSession, article_id: int) -> dict:
    if await _cache_tables_ready(db):
        row = (
            await db.execute(
                text(
                    """
                    SELECT i.article_id, a.title, a.slug, i.primary_url, i.index_status, i.citation_count,
                           i.scene_question_count, i.platforms_json, i.match_types_json,
                           i.citations_json, i.distributions_json, i.last_matched_at
                    FROM distribution_citation_index i
                    JOIN articles a ON a.id = i.article_id
                    WHERE i.article_id = :aid AND a.deleted_at IS NULL
                    """
                ),
                {"aid": article_id},
            )
        ).first()
        if row:
            platforms = row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]")
            match_types = row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]")
            citations = row[9] if isinstance(row[9], list) else json.loads(row[9] or "[]")
            distributions = row[10] if isinstance(row[10], list) else json.loads(row[10] or "[]")
            return {
                "status": "ok",
                "article": {"id": int(row[0]), "title": str(row[1]), "slug": str(row[2])},
                "article_id": int(row[0]),
                "title": str(row[1]),
                "primary_url": row[3],
                "index_status": str(row[4]),
                "citation_count": int(row[5] or 0),
                "scene_question_count": int(row[6] or 0),
                "platforms": platforms,
                "platform_labels": [PLATFORM_LABELS.get(p, p) for p in platforms],
                "match_types": match_types,
                "citations": citations,
                "distributions": distributions,
                "last_matched_at": row[11].isoformat() if row[11] else None,
                "stats": {
                    "citation_count": int(row[5] or 0),
                    "scene_question_count": int(row[6] or 0),
                    "platform_count": len(platforms),
                },
            }

    article = await db.get(Article, article_id)
    if article is None or article.deleted_at is not None:
        return {"status": "not_found", "article_id": article_id}

    dist_rows = (
        await db.execute(
            select(ArticleDistribution, DistributionChannel)
            .join(DistributionChannel, DistributionChannel.id == ArticleDistribution.channel_id)
            .where(
                ArticleDistribution.article_id == article_id,
                ArticleDistribution.status.in_(SYNCED_STATUSES),
            )
            .order_by(ArticleDistribution.id.desc())
        )
    ).all()

    article_urls: list[str] = []
    distributions: list[dict] = []
    for dist, channel in dist_rows:
        remote_url = (dist.remote_url or "").strip()
        if remote_url:
            article_urls.append(remote_url)
        distributions.append(
            {
                "distribution_id": dist.id,
                "channel_id": channel.id,
                "channel_name": channel.name,
                "channel_type": channel.channel_type,
                "remote_url": remote_url or None,
                "status": dist.status,
                "synced_at": dist.updated_at.isoformat() if dist.updated_at else None,
            }
        )

    if not distributions:
        return {
            "status": "ok",
            "article": {"id": article.id, "title": article.title, "slug": article.slug},
            "index_status": "not_distributed",
            "distributions": [],
            "citations": [],
            "stats": {"citation_count": 0, "scene_question_count": 0, "platform_count": 0},
        }

    bucket = {
        "article_id": article.id,
        "title": article.title,
        "article_urls": list(dict.fromkeys(article_urls)),
        "distributions": distributions,
    }
    citations = await _load_citation_records(db)
    has_probe_data = bool(citations) or await _has_probe_data(db)
    matched = _match_article_citations(bucket, citations, has_probe_data=has_probe_data)

    logger.info(
        "distribution_citation_detail article_id=%s status=%s citations=%s",
        article_id,
        matched["index_status"],
        matched["citation_count"],
    )
    return {
        "status": "ok",
        "article": {"id": article.id, "title": article.title, "slug": article.slug},
        **matched,
        "stats": {
            "citation_count": matched["citation_count"],
            "scene_question_count": matched["scene_question_count"],
            "platform_count": len(matched.get("platforms") or []),
        },
    }
