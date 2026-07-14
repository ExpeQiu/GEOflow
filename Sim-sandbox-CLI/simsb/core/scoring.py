"""排名加权分（对齐 GEOFlow RANK_WEIGHTS 契约）。"""

from __future__ import annotations

RANK_WEIGHTS = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


def calc_ranking_score(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return float(RANK_WEIGHTS.get(rank, 0))
