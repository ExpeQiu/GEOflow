from simsb.core.parser import extract_list_items, parse_answer


def test_list_order_numeric():
    text = "1. 比亚迪\n2. 吉利\n3. 小鹏"
    r = parse_answer(text, brand_list=["吉利"], competitor_brands=["比亚迪", "小鹏"])
    assert r.mentioned is True
    assert r.brand_rank == 2
    assert r.rank_method == "list_order"
    assert r.evidence_level == "L0"


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
