"""主栈 Rank v2 解析 — 不依赖 Sim-sandbox-CLI 运行时。"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.geoeval.answer_parser import PARSER_VERSION, extract_list_items, parse_answer

FIXTURES = Path(__file__).parent / "fixtures" / "probe_rank"


def test_list_order_numeric():
    text = "1. 比亚迪\n2. 吉利\n3. 小鹏"
    r = parse_answer(text, brand_list=["吉利"], competitor_brands=["比亚迪", "小鹏"])
    assert r.mentioned is True
    assert r.brand_rank == 2
    assert r.rank_method == "list_order"
    assert r.evidence_level == "L0"
    assert r.parser_version == PARSER_VERSION


def test_list_order_cn():
    text = "一、宁德时代\n二、比亚迪\n三、吉利"
    r = parse_answer(text, brand_list=["吉利"], competitor_brands=["宁德时代", "比亚迪"])
    assert r.brand_rank == 3
    assert r.rank_method == "list_order"


def test_first_mention_fallback():
    text = "特斯拉仍是标杆，其次是比亚迪，吉利也在追赶。"
    r = parse_answer(text, brand_list=["吉利"], competitor_brands=["比亚迪", "特斯拉"])
    assert r.mentioned is True
    assert r.brand_rank == 3
    assert r.rank_method == "first_mention"


def test_not_mentioned():
    text = "1. 比亚迪\n2. 特斯拉\n3. 蔚来"
    r = parse_answer(text, brand_list=["吉利"], competitor_brands=["比亚迪", "特斯拉"])
    assert r.mentioned is False
    assert r.brand_rank is None
    assert r.rank_method == "unknown"


def test_citation_wiki_l1():
    text = "参见 https://zh.wikipedia.org/wiki/Geely 提到吉利。"
    r = parse_answer(text, brand_list=["吉利"])
    assert r.evidence_level == "L1"
    assert r.match_type == "domain_wiki"


def test_citation_official_l1():
    text = "详见 https://www.geely.com/x 关于吉利。"
    r = parse_answer(text, brand_list=["吉利"], official_domains=["geely.com"])
    assert r.evidence_level == "L1"
    assert r.match_type == "domain_official"


def test_extract_list_items_count():
    items = extract_list_items("1. a\n2. b\n无关\n3. c")
    assert [i[0] for i in items] == [1, 2, 3]


def test_rank_fixtures_list_order_accuracy():
    path = FIXTURES / "list_order.jsonl"
    assert path.is_file(), "missing fixtures/probe_rank/list_order.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok = 0
    for row in rows:
        got = parse_answer(
            row["answer_text"],
            brand_list=row["brand_list"],
            competitor_brands=row.get("competitor_brands"),
        )
        exp = row["expected"]
        if (
            got.mentioned == exp["mentioned"]
            and got.brand_rank == exp.get("brand_rank")
            and got.rank_method == exp["rank_method"]
        ):
            ok += 1
    accuracy = ok / len(rows)
    # 对齐 probe_fixture_min_list_acc 默认 0.8（CI 不读 DB，避免耦合）
    min_acc = float(__import__("os").environ.get("PROBE_FIXTURE_MIN_LIST_ACC", "0.8"))
    assert accuracy >= min_acc, f"list_order accuracy {accuracy:.2%} < {min_acc:.0%} ({ok}/{len(rows)})"


def test_rank_fixtures_first_mention():
    path = FIXTURES / "first_mention.jsonl"
    assert path.is_file()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        got = parse_answer(
            row["answer_text"],
            brand_list=row["brand_list"],
            competitor_brands=row.get("competitor_brands"),
        )
        exp = row["expected"]
        assert got.mentioned == exp["mentioned"]
        assert got.brand_rank == exp.get("brand_rank")
        assert got.rank_method == exp["rank_method"]
