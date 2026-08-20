"""从明文 CoT 抽取六类信息分析框架，并发散长尾 Query。"""

from __future__ import annotations

import re
from typing import Any

FRAMEWORK_KEYS = (
    "sub_questions",
    "compare_dims",
    "evidence_bars",
    "scene_constraints",
    "open_gaps",
    "adjacent_queries",
)

_DIM_HINTS = ("对比", "维度", "方面", "指标", "怎么选", "哪个更")
_EVIDENCE_HINTS = ("数据", "实测", "证据", "冬测", "不能只看", "门槛", "第三方")
_SCENE_HINTS = ("场景", "冬天", "北方", "慢充", "城市", "长途", "代步", "沿海")
_GAP_HINTS = ("缺", "没有", "未知", "不敢", "未决", "缺少", "无法确认")
_ADJ_HINTS = ("还会问", "用户可能", "衍生", "进一步", "保费", "维修")
_SUB_HINTS = ("首先", "先澄清", "先分清", "先看", "再谈", "拆成")


def empty_framework() -> dict[str, list[str]]:
    return {k: [] for k in FRAMEWORK_KEYS}


def _lines(text: str) -> list[str]:
    raw = re.split(r"[\n。；;]+", text or "")
    out: list[str] = []
    seen: set[str] = set()
    for ln in raw:
        s = re.sub(r"^[\-\*\d\.、]+\s*", "", (ln or "").strip())
        if len(s) < 4:
            continue
        key = s[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(s[:160])
    return out


def _hit(line: str, hints: tuple[str, ...]) -> bool:
    return any(h in line for h in hints)


def extract_framework(thinking_text: str, *, scene_name: str = "", intent: str = "") -> dict[str, Any]:
    """规则抽取；无明文则空框架。不把 snippet/摘要当输入。"""
    fw = empty_framework()
    text = (thinking_text or "").strip()
    if len(text) < 8:
        fw["scene_name"] = scene_name
        fw["intent"] = intent
        fw["source"] = "empty"
        return fw

    for ln in _lines(text):
        if _hit(ln, _SUB_HINTS) and len(fw["sub_questions"]) < 6:
            fw["sub_questions"].append(ln)
        elif _hit(ln, _GAP_HINTS) and len(fw["open_gaps"]) < 6:
            fw["open_gaps"].append(ln)
        elif _hit(ln, _EVIDENCE_HINTS) and len(fw["evidence_bars"]) < 6:
            fw["evidence_bars"].append(ln)
        elif _hit(ln, _ADJ_HINTS) and len(fw["adjacent_queries"]) < 6:
            fw["adjacent_queries"].append(ln)
        elif _hit(ln, _SCENE_HINTS) and len(fw["scene_constraints"]) < 6:
            fw["scene_constraints"].append(ln)
        elif _hit(ln, _DIM_HINTS) and len(fw["compare_dims"]) < 6:
            fw["compare_dims"].append(ln)

    # 兜底：首句当拆解，含「安全/寿命/成本」的进维度
    if not fw["sub_questions"]:
        first = _lines(text)[:1]
        fw["sub_questions"] = first
    dim_words = ("安全", "寿命", "成本", "续航", "补能", "低温")
    for ln in _lines(text):
        if any(w in ln for w in dim_words) and ln not in fw["compare_dims"] and len(fw["compare_dims"]) < 6:
            fw["compare_dims"].append(ln)

    fw["scene_name"] = scene_name
    fw["intent"] = intent
    fw["source"] = "rule"
    return fw


def digest_framework(fw: dict[str, Any] | None) -> str:
    if not fw:
        return "暂无框架样本；请先跑 framework_api 扫描采集明文思维链。"
    parts: list[str] = []
    labels = {
        "sub_questions": "拆解",
        "compare_dims": "维度",
        "evidence_bars": "证据门槛",
        "scene_constraints": "场景约束",
        "open_gaps": "未决缺口",
        "adjacent_queries": "相邻问法",
    }
    for key, label in labels.items():
        items = [str(x).strip() for x in (fw.get(key) or []) if str(x).strip()]
        if items:
            parts.append(f"{label}：{' / '.join(items[:3])}")
    return "；".join(parts)[:800] if parts else "暂无框架样本；请先跑 framework_api 扫描采集明文思维链。"


def longtail_from_framework(
    fw: dict[str, Any] | None,
    *,
    scene_name: str = "",
    intent: str = "",
    probe_texts: list[str] | None = None,
) -> list[str]:
    """长尾 = 维度 × 场景约束 × 未决缺口；禁止等于探针原文。"""
    fw = fw or empty_framework()
    scene = (scene_name or str(fw.get("scene_name") or "") or "该场景").strip()
    intent_bit = (intent or str(fw.get("intent") or "") or "选型").strip()
    dims = [str(x)[:40] for x in (fw.get("compare_dims") or []) if str(x).strip()][:3]
    constraints = [str(x)[:40] for x in (fw.get("scene_constraints") or []) if str(x).strip()][:2] or [scene]
    gaps = [str(x)[:40] for x in (fw.get("open_gaps") or []) if str(x).strip()][:3]
    adjs = [str(x)[:80] for x in (fw.get("adjacent_queries") or []) if str(x).strip()][:3]

    seeds: list[str] = []
    for dim in dims or [intent_bit]:
        for cons in constraints:
            seeds.append(f"在{cons}条件下，{scene}该怎么比较「{dim}」？")
    for gap in gaps:
        seeds.append(f"{scene}决策前如何核实：{gap}？")
    seeds.extend(adjs)

    probe_norm = {re.sub(r"\s+", "", (p or "").strip().lower()) for p in (probe_texts or [])}
    out: list[str] = []
    seen: set[str] = set()
    for q in seeds:
        q = (q or "").strip()
        if not q:
            continue
        key = re.sub(r"\s+", "", q.lower())
        if key in seen or key in probe_norm:
            continue
        seen.add(key)
        out.append(q[:200])
        if len(out) >= 8:
            break
    return out
