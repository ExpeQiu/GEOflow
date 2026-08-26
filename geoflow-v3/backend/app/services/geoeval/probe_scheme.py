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

# 采集工作台卡片规格（与 engine 解绑）
SCHEME_CARD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "scheme": SCHEME_OPEN_API,
        "tracks": [TRACK_C],
        "label": "日常 C 轨",
        "kpi_note": "计入 visibility_open_api",
        "covers_kpi": True,
    },
    {
        "scheme": SCHEME_FRAMEWORK_API,
        "tracks": [TRACK_A, TRACK_C],
        "label": "A 框架轨",
        "kpi_note": "明文 CoT，不覆盖北极星",
        "covers_kpi": False,
    },
    {
        "scheme": SCHEME_CITATION,
        "tracks": [TRACK_B, TRACK_C],
        "label": "B 引用轨",
        "kpi_note": "答文 URL L1，不覆盖北极星",
        "covers_kpi": False,
    },
    {
        "scheme": SCHEME_CEND,
        "tracks": [TRACK_B, TRACK_C],
        "label": "C 端金标",
        "kpi_note": "资料链 L2，不覆盖北极星",
        "covers_kpi": False,
    },
)


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
        if engine == "skipped":
            outcome.reasoning_grade = GRADE_NONE
            tracks = []
        else:
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


def scheme_from_run_platform(platform: str | None) -> str:
    """从 geo_monitor_runs.platform 前缀推断 scheme（表未单独存 scan_type）。"""
    raw = (platform or "").strip().lower()
    if raw.startswith("framework_api"):
        return SCHEME_FRAMEWORK_API
    if raw.startswith("citation_grounded"):
        return SCHEME_CITATION
    if raw.startswith("cend"):
        return SCHEME_CEND
    return SCHEME_OPEN_API


def build_scheme_cards(
    *,
    probe_counts: dict[str, int] | None = None,
    latest_runs: dict[str, dict] | None = None,
    questions_estimated: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """四套 scheme 工作台卡片；缺数据补 0，顺序固定。"""
    counts = probe_counts or {}
    runs = latest_runs or {}
    est = questions_estimated or {}
    cards: list[dict[str, Any]] = []
    for spec in SCHEME_CARD_SPECS:
        scheme = str(spec["scheme"])
        cards.append(
            {
                **spec,
                "probe_count": int(counts.get(scheme, 0) or 0),
                "questions_estimated": int(est.get(scheme, 0) or 0),
                "latest_run": runs.get(scheme),
            }
        )
    return cards
