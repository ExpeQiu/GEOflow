"""夹具评测：解析结果 vs expected。"""

from __future__ import annotations

from typing import Any

from simsb.core.fixtures import load_fixtures
from simsb.core.parser import parse_answer
from simsb.utils.logger import get_logger

logger = get_logger("simsb.eval")

# 参与准确率统计的字段
COMPARE_FIELDS = ("mentioned", "brand_rank", "rank_method", "evidence_level")


def _match_field(predicted: Any, expected: Any) -> bool:
    if expected is None:
        return True  # 未标注的字段不判分
    return predicted == expected


def eval_case(case: dict[str, Any]) -> dict[str, Any]:
    brands = list(case.get("brand_list") or [])
    comps = list(case.get("competitor_brands") or [])
    official = list(case.get("official_domains") or [])
    wiki = list(case.get("wiki_domains") or []) or None
    parsed = parse_answer(
        case.get("answer_text") or "",
        brand_list=brands,
        competitor_brands=comps,
        wiki_domains=wiki,
        official_domains=official or None,
    )
    expected = case.get("expected") or {}
    field_ok: dict[str, bool] = {}
    for key in COMPARE_FIELDS:
        if key not in expected:
            continue
        field_ok[key] = _match_field(getattr(parsed, key), expected.get(key))

    checked = list(field_ok.keys())
    passed = all(field_ok.values()) if field_ok else False
    return {
        "id": case.get("id"),
        "passed": passed,
        "field_ok": field_ok,
        "checked_fields": checked,
        "predicted": parsed.to_dict(),
        "expected": expected,
        "platform": case.get("platform"),
        "question": case.get("question"),
    }


def run_eval_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [eval_case(c) for c in cases]
    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    # list_order 金样子集准确率（专题 DoD：≥80%）
    list_cases = [
        r
        for r in results
        if (r.get("expected") or {}).get("rank_method") == "list_order"
        and "brand_rank" in (r.get("expected") or {})
    ]
    list_ok = sum(
        1
        for r in list_cases
        if r["field_ok"].get("brand_rank") and r["field_ok"].get("rank_method", True)
    )
    list_acc = round(list_ok / len(list_cases), 3) if list_cases else None

    field_stats: dict[str, dict[str, int]] = {}
    for r in results:
        for k, ok in (r.get("field_ok") or {}).items():
            bucket = field_stats.setdefault(k, {"ok": 0, "n": 0})
            bucket["n"] += 1
            if ok:
                bucket["ok"] += 1

    logger.info(
        "eval_done total=%s passed=%s list_order_acc=%s",
        total,
        passed,
        list_acc,
    )
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "list_order_cases": len(list_cases),
        "list_order_accuracy": list_acc,
        "field_stats": {
            k: {
                "ok": v["ok"],
                "n": v["n"],
                "accuracy": round(v["ok"] / v["n"], 3) if v["n"] else 0.0,
            }
            for k, v in field_stats.items()
        },
        "results": results,
        "metric_kind": "fixture",
    }


def run_builtin_eval(fixtures_root) -> dict[str, Any]:
    """评测 fixtures/rank + fixtures/citation（跳过 samples）。"""
    from pathlib import Path

    root = Path(fixtures_root)
    cases: list[dict[str, Any]] = []
    for sub in ("rank", "citation"):
        p = root / sub
        if p.is_dir():
            cases.extend(load_fixtures(p))
    if not cases:
        cases = load_fixtures(root)
    return run_eval_cases(cases)


def run_eval(fixtures_path) -> dict[str, Any]:
    cases = load_fixtures(fixtures_path)
    return run_eval_cases(cases)
