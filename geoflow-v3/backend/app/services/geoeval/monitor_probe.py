"""GEO Monitor 探针 — 语料库启发式或 LLM 模拟平台回答。"""

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.knowledge import KnowledgeBase
from app.services.admin.production_service import _table_exists
from app.services.geoflow.llm_client import chat_json_or_mock

logger = logging.getLogger(__name__)

PLATFORMS = ("perplexity", "chatgpt", "gemini", "doubao")
PLATFORM_BIAS = {"perplexity": 0, "chatgpt": 1, "gemini": 2, "doubao": 1}
LLM_MAX_QUESTIONS = 5
PLATFORM_PROMPT = {
    "perplexity": "模拟 Perplexity 带引用摘要的搜索回答风格",
    "chatgpt": "模拟 ChatGPT 对话式回答风格",
    "gemini": "模拟 Google Gemini 综合回答风格",
    "doubao": "模拟豆包中文问答风格",
}


@dataclass
class ProbeOutcome:
    question_id: int
    platform: str
    brand_rank: int | None
    mentioned: bool
    snippet: str
    engine: str = "corpus"


async def load_brand_keywords(db: AsyncSession) -> list[str]:
    keywords: list[str] = [get_settings().app_name]
    if await _table_exists(db, "site_settings"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT setting_key, setting_value FROM site_settings
                    WHERE setting_key IN ('brand_name', 'brand_aliases')
                    """
                )
            )
        ).all()
        for key, value in rows:
            if not value:
                continue
            if key == "brand_aliases":
                keywords.extend([p.strip() for p in str(value).split(",") if p.strip()])
            else:
                keywords.append(str(value).strip())
    seen: set[str] = set()
    out: list[str] = []
    for kw in keywords:
        low = kw.lower()
        if low and low not in seen:
            seen.add(low)
            out.append(kw)
    return out[:12]


async def load_probe_mode(db: AsyncSession) -> str:
    if not await _table_exists(db, "site_settings"):
        return "corpus"
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_probe_mode' LIMIT 1")
        )
    ).scalar_one_or_none()
    return str(row) if row in ("corpus", "llm") else "corpus"


async def load_corpus(db: AsyncSession, limit: int = 80) -> list[dict]:
    corpus: list[dict] = []
    articles = (
        await db.execute(
            select(Article.title, Article.content)
            .where(Article.deleted_at.is_(None), Article.status == "published")
            .order_by(Article.id.desc())
            .limit(limit)
        )
    ).all()
    for title, content in articles:
        corpus.append({"title": title or "", "text": (content or "")[:3000]})

    kbs = (await db.execute(select(KnowledgeBase.name, KnowledgeBase.content).limit(20))).all()
    for name, content in kbs:
        corpus.append({"title": name or "", "text": (content or "")[:2000]})
    return corpus


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", text.lower())
    return set(parts)


def _score_doc(question: str, doc: dict, platform: str) -> float:
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 0.0
    blob = f"{doc.get('title', '')} {doc.get('text', '')}".lower()
    doc_tokens = _tokenize(blob)
    overlap = len(q_tokens & doc_tokens)
    base = overlap / max(len(q_tokens), 1)
    bias = PLATFORM_BIAS.get(platform, 0) * 0.02
    title_bonus = 0.15 if any(t in (doc.get("title") or "").lower() for t in q_tokens) else 0.0
    return base + title_bonus - bias


def _brand_in_text(text: str, brands: list[str]) -> bool:
    low = text.lower()
    return any(b.lower() in low for b in brands if b)


def _corpus_excerpt(corpus: list[dict], question_text: str, limit: int = 3) -> str:
    ranked = sorted(corpus, key=lambda d: _score_doc(question_text, d, "chatgpt"), reverse=True)[:limit]
    parts: list[str] = []
    for idx, doc in enumerate(ranked, start=1):
        parts.append(f"[{idx}] {doc.get('title', '')}\n{(doc.get('text') or '')[:600]}")
    return "\n\n".join(parts) if parts else "（无可用语料）"


def _probe_corpus(
    question_text: str,
    priority: int,
    platform: str,
    corpus: list[dict],
    brand_list: list[str],
) -> ProbeOutcome:
    ranked_docs = sorted(corpus, key=lambda d: _score_doc(question_text, d, "chatgpt"), reverse=True)[:10]
    platform_docs = sorted(corpus, key=lambda d: _score_doc(question_text, d, platform), reverse=True)[:10]

    rank: int | None = None
    snippet = ""
    for idx, doc in enumerate(platform_docs, start=1):
        blob = f"{doc['title']}\n{doc['text']}"
        if _brand_in_text(blob, brand_list):
            rank = idx + (1 if platform == "gemini" and priority > 70 else 0)
            snippet = blob[:240]
            break

    if rank is None and ranked_docs:
        top = ranked_docs[0]
        snippet = f"{top['title']}\n{top['text']}"[:240]
        if priority >= 80 and _brand_in_text(question_text, brand_list):
            rank = 3

    return ProbeOutcome(
        question_id=0,
        platform=platform,
        brand_rank=rank,
        mentioned=rank is not None,
        snippet=snippet,
        engine="corpus",
    )


async def _probe_llm(
    db: AsyncSession,
    *,
    question_text: str,
    platform: str,
    corpus: list[dict],
    brand_list: list[str],
) -> ProbeOutcome | None:
    style = PLATFORM_PROMPT.get(platform, "模拟 AI 搜索回答")
    brands = ", ".join(brand_list[:8])
    system = (
        f"你是 GEO 品牌监控探针。{style}。"
        "仅根据参考语料判断目标品牌是否被提及及相对排名。"
        '返回 JSON：{"mentioned": bool, "brand_rank": number|null, "snippet": "简短摘录"}'
    )
    user = (
        f"用户问题：{question_text}\n"
        f"监控品牌：{brands}\n"
        f"参考语料：\n{_corpus_excerpt(corpus, question_text)}\n"
        f"模拟平台：{platform}"
    )
    parsed = await chat_json_or_mock(db, system=system, user=user)
    if parsed is None:
        return None

    mentioned = bool(parsed.get("mentioned"))
    rank_raw = parsed.get("brand_rank")
    rank = int(rank_raw) if mentioned and rank_raw is not None else None
    snippet = str(parsed.get("snippet") or "")[:240]
    if mentioned and not snippet:
        snippet = _corpus_excerpt(corpus, question_text, limit=1)[:240]

    return ProbeOutcome(
        question_id=0,
        platform=platform,
        brand_rank=rank,
        mentioned=mentioned,
        snippet=snippet,
        engine="llm",
    )


async def _persist_probe(
    db: AsyncSession,
    *,
    run_id: int,
    outcome: ProbeOutcome,
) -> None:
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return
    params = {
        "run_id": run_id,
        "qid": outcome.question_id,
        "platform": outcome.platform,
        "rank": outcome.brand_rank,
        "mentioned": outcome.mentioned,
        "snippet": outcome.snippet,
        "engine": outcome.engine,
    }
    try:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_results
                    (run_id, question_id, platform, brand_rank, mentioned, snippet, engine)
                VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine)
                """
            ),
            params,
        )
    except Exception:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_results
                    (run_id, question_id, platform, brand_rank, mentioned, snippet)
                VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet)
                """
            ),
            {k: v for k, v in params.items() if k != "engine"},
        )


async def run_probes_for_questions(
    db: AsyncSession,
    *,
    run_id: int,
    questions: list[tuple[int, str, int]],
    brands: list[str] | None = None,
) -> list[ProbeOutcome]:
    brand_list = brands or await load_brand_keywords(db)
    corpus = await load_corpus(db)
    probe_mode = await load_probe_mode(db)
    outcomes: list[ProbeOutcome] = []

    for q_idx, (qid, question_text, priority) in enumerate(questions):
        use_llm = probe_mode == "llm" and q_idx < LLM_MAX_QUESTIONS

        for platform in PLATFORMS:
            outcome: ProbeOutcome | None = None
            if use_llm:
                outcome = await _probe_llm(
                    db,
                    question_text=question_text,
                    platform=platform,
                    corpus=corpus,
                    brand_list=brand_list,
                )
            if outcome is None:
                outcome = _probe_corpus(question_text, priority, platform, corpus, brand_list)
            outcome.question_id = qid
            outcomes.append(outcome)
            await _persist_probe(db, run_id=run_id, outcome=outcome)

    logger.info(
        "monitor_probes_completed run_id=%s questions=%s probes=%s mode=%s",
        run_id,
        len(questions),
        len(outcomes),
        probe_mode,
    )
    return outcomes


async def aggregate_probe_kpis(db: AsyncSession) -> dict:
    empty = {
        "probe_count": 0,
        "avg_brand_rank": None,
        "mention_rate": 0.0,
        "platform_summary": [],
    }
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return empty

    total = int(
        await db.scalar(text("SELECT COUNT(*) FROM geo_monitor_probe_results")) or 0
    )
    mentioned = int(
        await db.scalar(text("SELECT COUNT(*) FROM geo_monitor_probe_results WHERE mentioned = true")) or 0
    )
    avg_rank = await db.scalar(
        text(
            "SELECT AVG(brand_rank) FROM geo_monitor_probe_results WHERE brand_rank IS NOT NULL"
        )
    )
    platform_rows = (
        await db.execute(
            text(
                """
                SELECT platform,
                       COUNT(*) AS total,
                       SUM(CASE WHEN mentioned THEN 1 ELSE 0 END) AS mentions,
                       AVG(brand_rank) AS avg_rank
                FROM geo_monitor_probe_results
                GROUP BY platform
                ORDER BY platform
                """
            )
        )
    ).all()

    return {
        "probe_count": total,
        "avg_brand_rank": round(float(avg_rank), 2) if avg_rank is not None else None,
        "mention_rate": round(mentioned / total, 3) if total else 0.0,
        "platform_summary": [
            {
                "platform": str(r[0]),
                "total": int(r[1]),
                "mentions": int(r[2] or 0),
                "avg_rank": round(float(r[3]), 2) if r[3] is not None else None,
            }
            for r in platform_rows
        ],
    }
