from simsb.config import PKG_ROOT
from simsb.core.eval import run_builtin_eval, run_eval


def test_builtin_fixtures_pass_gate():
    report = run_builtin_eval(PKG_ROOT / "fixtures")
    assert report["total"] >= 20
    assert report["failed"] == 0
    assert report["list_order_accuracy"] is not None
    assert report["list_order_accuracy"] >= 0.8


def test_run_eval_single_file():
    path = PKG_ROOT / "fixtures" / "rank" / "first_mention.jsonl"
    report = run_eval(path)
    assert report["total"] == 3
    assert report["metric_kind"] == "fixture"
