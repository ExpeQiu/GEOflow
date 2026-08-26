"""Techstore 只读快照：吉利知识地图 / FAQ / 文档 / 门店知识。

不写 Techstore。无 `TECHSTORE_DATABASE_URL` 时用仓内 fixture（Mock First）。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "techstore_snapshot.json"
KB_NAME_PREFIX = "Geely/"
SOURCE_MARKER = "source:techstore"


@dataclass
class TechstoreSnapshot:
    source: str
    domains: list[dict[str, Any]] = field(default_factory=list)
    techniques: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    faqs: list[dict[str, Any]] = field(default_factory=list)
    knowledge_rows: list[dict[str, Any]] = field(default_factory=list)
    warning: str = ""

    def counts(self) -> dict[str, int]:
        return {
            "domains": len(self.domains),
            "techniques": len(self.techniques),
            "documents": len(self.published_documents()),
            "faqs": len(self.faqs),
            "knowledge_rows": len(self.knowledge_rows),
        }

    def published_documents(self) -> list[dict[str, Any]]:
        return [d for d in self.documents if str(d.get("status") or "").upper() == "PUBLISHED"]


def load_fixture_snapshot() -> TechstoreSnapshot:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return snapshot_from_dict(raw, source="fixture")


def snapshot_from_dict(raw: dict[str, Any], source: str) -> TechstoreSnapshot:
    return TechstoreSnapshot(
        source=source,
        domains=list(raw.get("domains") or []),
        techniques=list(raw.get("techniques") or []),
        documents=list(raw.get("documents") or []),
        faqs=list(raw.get("faqs") or []),
        knowledge_rows=list(raw.get("knowledge_rows") or []),
        warning=str(raw.get("warning") or ""),
    )


def wiki_slug_from_url(url: str | None) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    path = urlparse(raw).path if "://" in raw else raw
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return ""
    slug = parts[-1]
    slug = re.sub(r"\.(mdx|md)$", "", slug, flags=re.I)
    return slug[:200]


def make_ip_id(tech: dict[str, Any], used: set[str]) -> str:
    slug = wiki_slug_from_url(str(tech.get("wiki_url") or ""))
    candidate = slug or _ascii_slug(str(tech.get("name") or "")) or f"ts-{tech.get('id') or 'x'}"
    candidate = re.sub(r"[^a-zA-Z0-9._-]+", "-", candidate).strip("-")[:64] or f"ts-{tech.get('id') or 'x'}"
    base = candidate.lower()
    out = base
    n = 2
    while out in used:
        suffix = f"-{n}"
        out = (base[: 64 - len(suffix)] + suffix).lower()
        n += 1
    used.add(out)
    return out


def _ascii_slug(name: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return ascii_part[:40]


def ip_layer_from_depth(depth: Any) -> str:
    try:
        d = int(depth)
    except (TypeError, ValueError):
        d = 0
    return f"L{max(0, min(d, 3))}"


def build_tech_asset_rows(snapshot: TechstoreSnapshot) -> list[dict[str, Any]]:
    domain_name = {d.get("id"): str(d.get("name") or "") for d in snapshot.domains}
    used: set[str] = set()
    rows: list[dict[str, Any]] = []
    for tech in snapshot.techniques:
        name = str(tech.get("name") or "").strip()
        if not name:
            continue
        ip_id = make_ip_id(tech, used)
        wiki_slug = wiki_slug_from_url(str(tech.get("wiki_url") or "")) or None
        desc_parts = [
            str(tech.get("description") or "").strip(),
            str(tech.get("key_innovation") or "").strip(),
        ]
        description = "\n".join(p for p in desc_parts if p)
        alts = tech.get("alternative_names") or []
        if isinstance(alts, str):
            alts = [alts]
        rows.append(
            {
                "ip_id": ip_id,
                "name": name,
                "mind_tag": domain_name.get(tech.get("domain_id"), "")[:100],
                "ip_layer": ip_layer_from_depth(tech.get("depth")),
                "wiki_type": "concept",
                "wiki_slug": wiki_slug,
                "priority": int(tech.get("order") or 0) * 10 + int(tech.get("depth") or 0),
                "description": description[:4000],
                "status": "active",
                "meta_json": {
                    SOURCE_MARKER.split(":")[0]: "techstore",
                    "techstore_id": tech.get("id"),
                    "domain_id": tech.get("domain_id"),
                    "wiki_url": tech.get("wiki_url") or "",
                    "alternative_names": list(alts),
                    "tags": list(tech.get("tags") or []),
                    "vehicles": list(tech.get("vehicles") or []),
                    "definitions": tech.get("definitions") if isinstance(tech.get("definitions"), dict) else {},
                },
            }
        )
    return rows


def _domain_docs(snapshot: TechstoreSnapshot) -> dict[str, list[dict[str, Any]]]:
    by_domain: dict[str, list[dict[str, Any]]] = {str(d.get("name") or ""): [] for d in snapshot.domains}
    unassigned: list[dict[str, Any]] = []
    for doc in snapshot.published_documents():
        names = [str(n) for n in (doc.get("domain_names") or []) if str(n).strip()]
        if not names:
            unassigned.append(doc)
            continue
        for n in names:
            by_domain.setdefault(n, []).append(doc)
    if unassigned:
        by_domain.setdefault("文档", []).extend(unassigned)
    return by_domain


def _render_technique_md(tech: dict[str, Any]) -> str:
    lines = [f"## 技术点：{tech.get('name')}"]
    wiki = str(tech.get("wiki_url") or "").strip()
    if wiki:
        lines.append(f"- Wiki: `{wiki}`")
    alts = tech.get("alternative_names") or []
    if alts:
        lines.append(f"- 别名: {', '.join(str(a) for a in alts)}")
    tags = tech.get("tags") or []
    if tags:
        lines.append(f"- 标签: {', '.join(str(t) for t in tags)}")
    desc = str(tech.get("description") or "").strip()
    if desc:
        lines.extend(["", desc])
    inn = str(tech.get("key_innovation") or "").strip()
    if inn:
        lines.extend(["", f"### 关键创新\n\n{inn}"])
    defs = tech.get("definitions")
    if isinstance(defs, dict) and defs:
        lines.append("\n### 定义")
        for k, v in defs.items():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines).strip()


def _render_document_md(doc: dict[str, Any]) -> str:
    lines = [f"## 文档：{doc.get('title')}"]
    slug = str(doc.get("slug") or "").strip()
    if slug:
        lines.append(f"- slug: `{slug}`")
    summary = str(doc.get("summary") or "").strip()
    if summary:
        lines.extend(["", summary])
    ai_summary = str(doc.get("ai_summary") or "").strip()
    if ai_summary:
        lines.extend(["", f"**AI 摘要**：{ai_summary}"])
    text = str(doc.get("text") or "").strip()
    if text:
        lines.extend(["", text])
    return "\n".join(lines).strip()


def build_kb_payloads(snapshot: TechstoreSnapshot) -> list[dict[str, str]]:
    """按域拆 KB：地图语料 + 已发布文档；另建 FAQ / 门店知识。"""
    payloads: list[dict[str, str]] = []
    tech_by_domain: dict[str, list[dict[str, Any]]] = {str(d.get("id")): [] for d in snapshot.domains}
    for tech in snapshot.techniques:
        tech_by_domain.setdefault(str(tech.get("domain_id")), []).append(tech)
    docs_by_domain = _domain_docs(snapshot)

    for domain in snapshot.domains:
        name = str(domain.get("name") or "").strip()
        if not name:
            continue
        sections = [
            f"# 吉利技术知识 · {name}",
            f"> {SOURCE_MARKER} domain=`{name}` 只读导入，勿在本库手改后当 SSOT。",
        ]
        ddesc = str(domain.get("description") or "").strip()
        if ddesc:
            sections.append(ddesc)
        for tech in tech_by_domain.get(str(domain.get("id")), []):
            sections.append(_render_technique_md(tech))
        for doc in docs_by_domain.get(name, []):
            sections.append(_render_document_md(doc))
        body = "\n\n".join(s for s in sections if s).strip()
        if len(body.split()) < 8:
            continue
        payloads.append(
            {
                "name": f"{KB_NAME_PREFIX}{name}"[:100],
                "description": f"Techstore 领域「{name}」语料（{SOURCE_MARKER}）",
                "content": body,
            }
        )

    extra_docs = docs_by_domain.get("文档") or []
    if extra_docs:
        sections = [
            f"# 吉利技术文档",
            f"> {SOURCE_MARKER} 未挂领域的已发布文档。",
        ]
        sections.extend(_render_document_md(d) for d in extra_docs)
        payloads.append(
            {
                "name": f"{KB_NAME_PREFIX}文档"[:100],
                "description": f"Techstore 未分域文档（{SOURCE_MARKER}）",
                "content": "\n\n".join(sections),
            }
        )

    if snapshot.faqs:
        faq_parts = [f"# 吉利 FAQ", f"> {SOURCE_MARKER}"]
        for faq in snapshot.faqs:
            q = str(faq.get("question") or "").strip()
            a = str(faq.get("answer") or "").strip()
            if not q or not a:
                continue
            tags = ", ".join(str(t) for t in (faq.get("tags") or []) if str(t).strip())
            block = f"## Q: {q}\n\n{a}"
            if tags:
                block += f"\n\n标签: {tags}"
            faq_parts.append(block)
        if len(faq_parts) > 2:
            payloads.append(
                {
                    "name": f"{KB_NAME_PREFIX}FAQ"[:100],
                    "description": f"Techstore FAQ（{SOURCE_MARKER}）",
                    "content": "\n\n".join(faq_parts),
                }
            )

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for row in snapshot.knowledge_rows:
        cat = str(row.get("category") or "门店").strip() or "门店"
        by_cat.setdefault(cat, []).append(row)
    for cat, rows in by_cat.items():
        parts = [f"# 吉利门店知识 · {cat}", f"> {SOURCE_MARKER}"]
        for row in rows:
            title = str(row.get("title") or "").strip() or "条目"
            content = str(row.get("content") or "").strip()
            if not content:
                continue
            parts.append(f"## {title}\n\n{content}")
        if len(parts) > 2:
            payloads.append(
                {
                    "name": f"{KB_NAME_PREFIX}{cat}"[:100],
                    "description": f"Techstore knowledge 表 / {cat}（{SOURCE_MARKER}）",
                    "content": "\n\n".join(parts),
                }
            )
    return payloads


def preview_from_snapshot(snapshot: TechstoreSnapshot) -> dict[str, Any]:
    assets = build_tech_asset_rows(snapshot)
    kbs = build_kb_payloads(snapshot)
    return {
        "source": snapshot.source,
        "warning": snapshot.warning,
        "counts": snapshot.counts(),
        "asset_count": len(assets),
        "kb_names": [k["name"] for k in kbs],
        "connected": snapshot.source == "live",
    }


def fetch_live_snapshot(database_url: str) -> TechstoreSnapshot:
    """同步只读拉取。调用方应放到线程，避免堵住事件循环。"""
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(database_url, connect_timeout=8)
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        tables = _list_tables(cur)
        domains = _fetch_rows(cur, tables, ["Domain", "domain"], "ORDER BY \"order\"")
        techniques = _fetch_techniques(cur, tables)
        documents = _fetch_documents(cur, tables)
        faqs = _fetch_faqs(cur, tables)
        knowledge_rows = _fetch_knowledge(cur, tables)
        _attach_technique_meta(cur, tables, techniques)
        _attach_document_domains(cur, tables, documents, techniques, domains)
        snap = TechstoreSnapshot(
            source="live",
            domains=[_norm_domain(r) for r in domains],
            techniques=techniques,
            documents=documents,
            faqs=faqs,
            knowledge_rows=knowledge_rows,
        )
        logger.info(
            "techstore_snapshot_live domains=%s techniques=%s docs=%s faqs=%s knowledge=%s",
            len(snap.domains),
            len(snap.techniques),
            len(snap.published_documents()),
            len(snap.faqs),
            len(snap.knowledge_rows),
        )
        return snap
    finally:
        conn.close()


def _list_tables(cur: Any) -> set[str]:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    return {str(r["tablename"] if isinstance(r, dict) else r[0]) for r in cur.fetchall()}


def _qi(name: str) -> str:
    return '"' + name.replace('"', "") + '"'


def _pick_table(tables: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in tables:
            return c
    lower = {t.lower(): t for t in tables}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def _fetch_rows(cur: Any, tables: set[str], candidates: list[str], extra_sql: str = "") -> list[dict[str, Any]]:
    table = _pick_table(tables, candidates)
    if not table:
        return []
    cur.execute(f"SELECT * FROM {_qi(table)} {extra_sql}")
    return [dict(r) for r in cur.fetchall()]


def _norm_domain(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "name": str(row.get("name") or ""),
        "description": str(row.get("description") or ""),
    }


def _fetch_techniques(cur: Any, tables: set[str]) -> list[dict[str, Any]]:
    rows = _fetch_rows(cur, tables, ["Technique", "technique"], 'ORDER BY "order"')
    out: list[dict[str, Any]] = []
    for r in rows:
        alts = r.get("alternativeName") or r.get("alternative_names") or []
        if not isinstance(alts, list):
            alts = []
        defs = r.get("definitions")
        if isinstance(defs, str):
            try:
                defs = json.loads(defs)
            except json.JSONDecodeError:
                defs = {}
        out.append(
            {
                "id": str(r.get("id") or ""),
                "domain_id": str(r.get("domainId") or r.get("domain_id") or ""),
                "parent_id": r.get("parentId") or r.get("parent_id"),
                "name": str(r.get("name") or ""),
                "description": str(r.get("description") or ""),
                "key_innovation": str(r.get("keyInnovation") or r.get("key_innovation") or ""),
                "wiki_url": str(r.get("wikiUrl") or r.get("wiki_url") or ""),
                "order": int(r.get("order") or 0),
                "depth": int(r.get("depth") or 0),
                "alternative_names": alts,
                "definitions": defs if isinstance(defs, dict) else {},
                "tags": [],
                "vehicles": [],
            }
        )
    return out


def _attach_technique_meta(cur: Any, tables: set[str], techniques: list[dict[str, Any]]) -> None:
    by_id = {t["id"]: t for t in techniques}
    tag_table = _pick_table(tables, ["Tag", "tag"])
    tt_table = _pick_table(tables, ["TechniqueTag", "technique_tags"])
    if tag_table and tt_table:
        cur.execute(
            f"""
            SELECT tt."techniqueId" AS tid, t.name
            FROM {_qi(tt_table)} tt
            JOIN {_qi(tag_table)} t ON t.id = tt."tagId"
            """
        )
        for r in cur.fetchall():
            row = dict(r)
            tech = by_id.get(str(row.get("tid") or ""))
            if tech:
                tech["tags"].append(str(row.get("name") or ""))
    vt_table = _pick_table(tables, ["VehicleTag", "vehicle_tags", "VehicleTag"])
    tv_table = _pick_table(tables, ["TechniqueVehicleTag", "technique_vehicle_tags"])
    if vt_table and tv_table:
        cur.execute(
            f"""
            SELECT tv."techniqueId" AS tid, v.name
            FROM {_qi(tv_table)} tv
            JOIN {_qi(vt_table)} v ON v.id = tv."vehicleTagId"
            """
        )
        for r in cur.fetchall():
            row = dict(r)
            tech = by_id.get(str(row.get("tid") or ""))
            if tech:
                tech["vehicles"].append(str(row.get("name") or ""))


def _table_columns(cur: Any, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    return {str(r["column_name"] if isinstance(r, dict) else r[0]) for r in cur.fetchall()}


def _fetch_documents(cur: Any, tables: set[str]) -> list[dict[str, Any]]:
    doc_table = _pick_table(tables, ["Document", "document"])
    if not doc_table:
        return []
    cols = _table_columns(cur, doc_table)
    cat_table = _pick_table(tables, ["Category", "category"])
    join_sql = ""
    if cat_table and ("categoryId" in cols or "category_id" in cols):
        cat_fk = "categoryId" if "categoryId" in cols else "category_id"
        join_sql = f"LEFT JOIN {_qi(cat_table)} c ON c.id = d.{_qi(cat_fk)}"
    where = ""
    if "deletedAt" in cols:
        where = 'WHERE d."deletedAt" IS NULL'
    elif "deleted_at" in cols:
        where = "WHERE d.deleted_at IS NULL"
    cur.execute(
        f"""
        SELECT d.*, {('c.name AS category_name' if join_sql else "NULL AS category_name")}
        FROM {_qi(doc_table)} d
        {join_sql}
        {where}
        """
    )
    docs: list[dict[str, Any]] = []
    for r in cur.fetchall():
        row = dict(r)
        docs.append(
            {
                "id": str(row.get("id") or ""),
                "title": str(row.get("title") or ""),
                "slug": str(row.get("slug") or ""),
                "summary": str(row.get("summary") or ""),
                "ai_summary": str(row.get("aiSummary") or row.get("ai_summary") or ""),
                "status": str(row.get("status") or ""),
                "category": str(row.get("category_name") or ""),
                "domain_names": [],
                "technique_names": [],
                "text": "",
            }
        )
    return docs


def _attach_document_domains(
    cur: Any,
    tables: set[str],
    documents: list[dict[str, Any]],
    techniques: list[dict[str, Any]],
    domains: list[dict[str, Any]],
) -> None:
    by_doc = {d["id"]: d for d in documents}
    tech_by_id = {t["id"]: t for t in techniques}
    domain_by_id = {str(d.get("id")): str(d.get("name") or "") for d in domains}
    link = _pick_table(tables, ["TechniqueDocument", "technique_documents", "_TechniqueToDocument"])
    if not link:
        return
    # Prisma implicit many-to-many 表名不确定，探测列
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (link,),
    )
    cols = {str(r["column_name"] if isinstance(r, dict) else r[0]) for r in cur.fetchall()}
    tech_col = "techniqueId" if "techniqueId" in cols else ("A" if "A" in cols else None)
    doc_col = "documentId" if "documentId" in cols else ("B" if "B" in cols else None)
    if not tech_col or not doc_col:
        return
    cur.execute(f"SELECT {_qi(tech_col)} AS tid, {_qi(doc_col)} AS did FROM {_qi(link)}")
    for r in cur.fetchall():
        row = dict(r)
        doc = by_doc.get(str(row.get("did") or ""))
        tech = tech_by_id.get(str(row.get("tid") or ""))
        if not doc or not tech:
            continue
        dname = domain_by_id.get(str(tech.get("domain_id") or ""), "")
        if dname and dname not in doc["domain_names"]:
            doc["domain_names"].append(dname)
        tname = str(tech.get("name") or "")
        if tname and tname not in doc["technique_names"]:
            doc["technique_names"].append(tname)


def _fetch_faqs(cur: Any, tables: set[str]) -> list[dict[str, Any]]:
    faq_table = _pick_table(tables, ["faq_items", "FaqItem"])
    if not faq_table:
        return []
    cur.execute(f'SELECT * FROM {_qi(faq_table)} ORDER BY "order"')
    faqs = []
    by_id: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        row = dict(r)
        item = {
            "id": str(row.get("id") or ""),
            "question": str(row.get("question") or ""),
            "answer": str(row.get("answer") or ""),
            "tags": [],
        }
        faqs.append(item)
        by_id[item["id"]] = item
    tag_table = _pick_table(tables, ["faq_tags"])
    link = _pick_table(tables, ["faq_item_tags"])
    if tag_table and link:
        cur.execute(
            f"""
            SELECT l."faqItemId" AS fid, t.name
            FROM {_qi(link)} l
            JOIN {_qi(tag_table)} t ON t.id = l."faqTagId"
            """
        )
        for r in cur.fetchall():
            row = dict(r)
            item = by_id.get(str(row.get("fid") or ""))
            if item:
                item["tags"].append(str(row.get("name") or ""))
    return faqs


def _fetch_knowledge(cur: Any, tables: set[str]) -> list[dict[str, Any]]:
    table = _pick_table(tables, ["knowledge"])
    if not table:
        return []
    cur.execute(f"SELECT id, title, content, category, tags FROM {_qi(table)} ORDER BY id")
    rows = []
    for r in cur.fetchall():
        row = dict(r)
        rows.append(
            {
                "id": row.get("id"),
                "title": str(row.get("title") or ""),
                "content": str(row.get("content") or ""),
                "category": str(row.get("category") or "门店"),
                "tags": str(row.get("tags") or ""),
            }
        )
    return rows
