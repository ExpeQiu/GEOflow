"""三层探针口径：scheme / tracks / reasoning_grade（ADR-012）。"""

from __future__ import annotations

from typing import Any, Iterable

SCHEME_OPEN_API = "open_api"
SCHEME_FRAMEWORK_API = "framework_api"
SCHEME_CITATION = "citation_grounded"
SCHEME_CEND = "cend_sample"
SCHEME_DEV = "dev_sim"

SCHEMES = (
    SCHEME_OPEN_API,
    SCHEME_FRAMEWORK_API,
    SCHEME_CITATION,
    SCHEME_CEND,
    SCHEME_DEV,
)

TRACK_A = "A"
TRACK_B = "B"
TRACK_C = "C"
TRACK_ORDER = (TRACK_A, TRACK_B, TRACK_C)

GRADE_RAW = "raw"
GRADE_SUMMARY = "summary"
GRADE_NONE = "none"

METRIC_OPEN_API = "open_api"
METRIC_FRAMEWORK = "framework_sample"
METRIC_CEND = "cend_sample"
METRIC_CITATION = "citation_sample"
METRIC_MIXED = "mixed"

KPI_EXCLUDED_METRICS = frozenset({METRIC_CEND, METRIC_FRAMEWORK, METRIC_CITATION})


def ordered_tracks(tracks: Iterable[str]) -> list[str]:
    seen = {str(t).strip().upper() for t in tracks if str(t).strip()}
    return [t for t in TRACK_ORDER if t in seen]


def north_star_sql_filters(*, alias: str = "pr", has_scheme_col: bool = False) -> str:
    """北极星 SQL 片段：真实 API 的 C 轨日扫，排除框架/C 端/引用辅轨。"""
    sql = f" AND COALESCE({alias}.engine, 'corpus') = 'api'"
    sql += (
        f" AND COALESCE({alias}.metric_kind, 'mixed') "
        f"NOT IN ('{METRIC_CEND}', '{METRIC_FRAMEWORK}', '{METRIC_CITATION}')"
    )
    if has_scheme_col:
        sql += f" AND COALESCE({alias}.scheme, '{SCHEME_OPEN_API}') = '{SCHEME_OPEN_API}'"
    return sql


def stamp_outcome(outcome: Any, *, scheme: str) -> Any:
    """按方案给 ProbeOutcome 打口径；不覆盖调用方已显式设置的 grade/tracks。"""
    scheme = scheme if scheme in SCHEMES else SCHEME_OPEN_API
    outcome.scheme = scheme

    thinking = (getattr(outcome, "thinking_text", None) or "").strip()
    cites = list(getattr(outcome, "citation_urls", None) or []) or list(getattr(outcome, "urls", None) or [])
    engine = getattr(outcome, "engine", "") or ""

    if scheme == SCHEME_FRAMEWORK_API:
        outcome.metric_kind = METRIC_FRAMEWORK
        outcome.reasoning_grade = GRADE_RAW if thinking else GRADE_NONE
        tracks = [TRACK_C]
        if thinking:
            tracks.insert(0, TRACK_A)
        if cites:
            tracks.insert(-1, TRACK_B)
    elif scheme == SCHEME_CEND:
        outcome.metric_kind = METRIC_CEND
        outcome.reasoning_grade = GRADE_SUMMARY if thinking else GRADE_NONE
        tracks = [TRACK_C]
        if cites:
            tracks.insert(0, TRACK_B)
        # C 端思考仅辅证，不进 A 轨 KPI
    elif scheme == SCHEME_CITATION:
        outcome.metric_kind = METRIC_CITATION
        outcome.reasoning_grade = GRADE_NONE
        tracks = [TRACK_C]
        if cites:
            tracks.insert(0, TRACK_B)
    elif scheme == SCHEME_OPEN_API and engine == "api":
        if not getattr(outcome, "metric_kind", None) or outcome.metric_kind == "mixed":
            outcome.metric_kind = METRIC_OPEN_API
        # 日扫即使偶发 CoT 也不把 A 写入 tracks，避免混进框架扫描语义
        outcome.reasoning_grade = GRADE_NONE
        tracks = [TRACK_C]
        if cites:
            tracks.insert(0, TRACK_B)
    else:
        outcome.reasoning_grade = GRADE_NONE
        if not getattr(outcome, "metric_kind", None):
            outcome.metric_kind = METRIC_MIXED
        tracks = [TRACK_C] if engine != "skipped" else []

    outcome.tracks = ordered_tracks(tracks)
    return outcome
