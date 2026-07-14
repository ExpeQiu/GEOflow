"""Open-API vs 金标偏移对照 → 校准建议（不改写主 KPI）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from simsb.utils.errors import FixtureError, UsageError
from simsb.utils.logger import get_logger

logger = get_logger("simsb.calibrate")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FixtureError(f"文件不存在: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FixtureError(f"{path}:{lineno} JSON 无效: {exc}") from exc
        if not isinstance(obj, dict):
            raise FixtureError(f"{path}:{lineno} 期望 object")
        rows.append(obj)
    return rows


def _key(row: dict[str, Any]) -> tuple[str, str]:
    qid = str(row.get("question_id") or row.get("id") or "")
    platform = str(row.get("platform") or "")
    if not qid or not platform:
        raise UsageError(f"对照行缺少 question_id/id 或 platform: {row}")
    return qid, platform


def compute_bias(
    open_api_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_map = {_key(r): r for r in gold_rows}
    pairs: list[dict[str, Any]] = []
    mention_deltas: list[float] = []
    rank_deltas: list[float] = []

    for api in open_api_rows:
        k = _key(api)
        gold = gold_map.get(k)
        if not gold:
            continue
        api_m = bool(api.get("mentioned"))
        gold_m = bool(gold.get("mentioned"))
        api_r = api.get("brand_rank")
        gold_r = gold.get("brand_rank")
        m_delta = float(api_m) - float(gold_m)
        mention_deltas.append(m_delta)
        r_delta = None
        if api_r is not None and gold_r is not None:
            r_delta = float(api_r) - float(gold_r)
            rank_deltas.append(r_delta)
        pairs.append(
            {
                "question_id": k[0],
                "platform": k[1],
                "open_api": {"mentioned": api_m, "brand_rank": api_r},
                "cend_sample": {"mentioned": gold_m, "brand_rank": gold_r},
                "mention_delta": m_delta,
                "rank_delta": r_delta,
            }
        )

    def _mean(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    mean_m = _mean(mention_deltas)
    mean_r = _mean(rank_deltas)

    # 策略旋钮建议（仅建议，不自动写回生产）
    suggestions: dict[str, Any] = {
        "report_footnote": True,
        "do_not_overwrite_open_api_kpi": True,
        "rank": {
            "report_weight": {
                "list_order": 1.0,
                "first_mention": 0.3 if (mean_r is not None and abs(mean_r) >= 0.5) else 0.5,
            }
        },
        "scan": {},
    }
    if mean_m is not None and abs(mean_m) >= 0.2:
        suggestions["alert"] = {
            "mention_bias_abs_gte": 0.2,
            "observed_mean_mention_delta": mean_m,
            "note": "Open-API 提及相对金标偏移较大，报告需加可信度脚注",
        }

    logger.info(
        "bias_computed pairs=%s mean_mention_delta=%s mean_rank_delta=%s",
        len(pairs),
        mean_m,
        mean_r,
    )
    return {
        "metric_kind": "bias_report",
        "paired": len(pairs),
        "open_api_rows": len(open_api_rows),
        "gold_rows": len(gold_rows),
        "mean_mention_delta": mean_m,
        "mean_rank_delta": mean_r,
        "pairs": pairs,
        "suggestions": suggestions,
    }


def run_calibrate(
    *,
    open_api_path: Path,
    gold_path: Path,
    calibration_path: Path | None = None,
) -> dict[str, Any]:
    report = compute_bias(_load_jsonl(open_api_path), _load_jsonl(gold_path))
    if calibration_path and calibration_path.is_file():
        try:
            current = yaml.safe_load(calibration_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("calibration_load_failed path=%s error=%s", calibration_path, exc)
            current = {}
        report["current_calibration"] = current
    return report
