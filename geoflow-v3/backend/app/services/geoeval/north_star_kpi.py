"""北极星 KPI 纯函数：TopN 概率、竞品 pp、题型子集。"""

from __future__ import annotations

from typing import Iterable, Sequence

NORTH_STAR_INTENTS = frozenset({"compare", "decision"})
INTENT_TYPES = frozenset({"compare", "decision", "cognition", "risk"})


def normalize_intent_type(raw: str | None) -> str:
    v = (raw or "cognition").strip().lower()
    return v if v in INTENT_TYPES else "cognition"


def is_north_star_intent(intent_type: str | None) -> bool:
    return normalize_intent_type(intent_type) in NORTH_STAR_INTENTS


def topn_pct(ranks: Sequence[int | None], n: int) -> float | None:
    """有效样本（有可解析 rank）中进入 TopN 的占比。"""
    valid = [int(r) for r in ranks if r is not None and int(r) > 0]
    if not valid:
        return None
    hit = sum(1 for r in valid if r <= n)
    return round(hit / len(valid) * 100, 1)


def mention_rate_pct(mentioned: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(mentioned / total * 100, 1)


def sentiment_negative_pct(positive: int, neutral: int, negative: int) -> float | None:
    total = positive + neutral + negative
    if total <= 0:
        return None
    return round(negative / total * 100, 1)


def gap_vs_leader_pp(self_pct: float | None, leader_pct: float | None) -> float | None:
    """目标 − 最强竞品；正值=领先。"""
    if self_pct is None or leader_pct is None:
        return None
    return round(float(self_pct) - float(leader_pct), 1)


def win_rate_pct(wins: int, compare_samples: int) -> float | None:
    if compare_samples <= 0:
        return None
    return round(wins / compare_samples * 100, 1)


def classify_domain_from_text(text: str) -> str | None:
    t = (text or "").lower()
    rules = (
        ("智驾", "智驾"),
        ("noa", "智驾"),
        ("ads", "智驾"),
        ("三电", "三电"),
        ("电池", "三电"),
        ("电机", "三电"),
        ("座舱", "座舱"),
        ("芯片", "座舱"),
        ("安全", "安全"),
        ("中保研", "安全"),
    )
    for needle, domain in rules:
        if needle in t:
            return domain
    return None


def aggregate_domain_top3(
    samples: Iterable[tuple[str | None, int | None]],
) -> dict[str, float | None]:
    """samples: (domain, brand_rank) → domain -> top3_pct."""
    buckets: dict[str, list[int | None]] = {"三电": [], "智驾": [], "座舱": [], "安全": []}
    for domain, rank in samples:
        if domain in buckets:
            buckets[domain].append(rank)
    return {k: topn_pct(v, 3) for k, v in buckets.items()}
