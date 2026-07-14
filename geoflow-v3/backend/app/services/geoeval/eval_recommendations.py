"""GEO 评估 → 可操作建议（软门禁口径，不拦截发布）。"""

from __future__ import annotations

_ISSUE_HINTS: dict[str, str] = {
    "simulation_score_low": "提高正文与场景题/关键词重合，并将本稿同步进知识库后再评",
    "audit_failed": "补充分层小标题、列表或表格，强化可被检索摘录的结构化段落",
    "missing_quick_answer": "补充 wiki_meta.quick_answer 一句话速答",
    "missing_table": "正文增加对比/参数类 Markdown 表格",
    "insufficient_internal_links": "补充至少 3 条站内链接（](/… )）",
    "insufficient_faq": "wiki_meta.faq 至少保留 2 条常见问答",
    "missing_last_updated": "补充 wiki_meta.last_updated 日期",
}


def _issue_key(raw: str) -> str:
    return (raw or "").split(":", 1)[0].strip()


def build_recommendations(
    *,
    issues: list[str],
    simulation_score: float | None = None,
    audit_score: float | None = None,
    pass_score: float | None = None,
) -> list[dict]:
    """将失败码转为建议列表；同 key 去重，保留顺序。"""
    seen: set[str] = set()
    out: list[dict] = []
    for raw in issues:
        key = _issue_key(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        hint = _ISSUE_HINTS.get(key, f"关注指标：{raw}")
        item: dict = {"code": key, "detail": raw, "suggestion": hint}
        if key == "simulation_score_low" and simulation_score is not None:
            item["simulation_score"] = round(float(simulation_score), 4)
            if pass_score is not None:
                item["pass_score"] = float(pass_score)
        if key.startswith("audit") and audit_score is not None:
            item["audit_score"] = round(float(audit_score), 4)
        out.append(item)
    return out
