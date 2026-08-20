"""Theme 级 lift 题集解析。"""

from app.services.geoeval.monitor_probe import resolve_lift_question_ids


def test_lift_prefers_evidence_ids():
    ids = resolve_lift_question_ids(
        evidence_ids=[{"id": 11}, {"question_id": 12}, 12],
        target_queries=["家用纯电怎么选"],
        questions=[(99, "家用纯电怎么选续航")],
    )
    assert ids == [11, 12]


def test_lift_matches_target_queries():
    ids = resolve_lift_question_ids(
        evidence_ids=[],
        target_queries=["家用纯电怎么选续航"],
        questions=[
            (1, "家用纯电怎么选续航和空间"),
            (2, "智驾怎么买"),
            (3, "家用纯电怎么选续航"),
        ],
    )
    assert ids == [1, 3]


def test_lift_empty_falls_back_scene():
    assert resolve_lift_question_ids() == []
    assert resolve_lift_question_ids(target_queries=["x"]) == []
