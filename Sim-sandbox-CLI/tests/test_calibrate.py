from simsb.config import PKG_ROOT
from simsb.core.calibrate import run_calibrate


def test_calibrate_demo_samples():
    report = run_calibrate(
        open_api_path=PKG_ROOT / "fixtures" / "samples" / "open_api.jsonl",
        gold_path=PKG_ROOT / "fixtures" / "samples" / "gold.jsonl",
        calibration_path=PKG_ROOT / "config" / "calibration.yml",
    )
    assert report["paired"] == 4
    assert report["mean_mention_delta"] is not None
    assert report["suggestions"]["do_not_overwrite_open_api_kpi"] is True
    assert "current_calibration" in report
