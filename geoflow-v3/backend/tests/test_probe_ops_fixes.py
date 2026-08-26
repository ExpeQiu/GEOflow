"""P0/P1：日扫 SQL、官域保底、品牌别名 JSON。"""

from __future__ import annotations

from pathlib import Path

from app.services.geoeval.answer_parser import parse_answer
from app.services.geoeval.domain_catalog import (
    DEFAULT_OFFICIAL_DOMAINS,
    OWNER_OURS,
    classify_owner,
)
from app.services.geoeval.monitor_probe import parse_brand_aliases
from app.services.geoeval.sentiment_analyzer import batch_analyze_probe_sentiments


def test_sentiment_sql_avoids_json_eq_json():
    src = Path(batch_analyze_probe_sentiments.__code__.co_filename).read_text(encoding="utf-8")
    assert "sentiment = 'null'::json" not in src
    assert "CAST(sentiment AS TEXT)" in src


def test_parse_brand_aliases_json_array():
    assert parse_brand_aliases('["吉利", "Geely", "银河", "极氪"]') == ["吉利", "Geely", "银河", "极氪"]


def test_parse_brand_aliases_comma():
    assert parse_brand_aliases("吉利, 银河") == ["吉利", "银河"]


def test_galaxy_mentioned_with_json_aliases():
    aliases = parse_brand_aliases('["吉利", "Geely", "银河", "极氪"]')
    text = (
        "在20万级家用纯电SUV市场，**吉利银河**和**比亚迪唐EV**确实是两个很有代表性的选择。"
    )
    r = parse_answer(text, brand_list=["吉利汽车", *aliases], competitor_brands=["比亚迪"])
    assert r.mentioned is True


def test_geely_com_ours_with_default_official():
    assert "geely.com" in DEFAULT_OFFICIAL_DOMAINS
    assert classify_owner("https://www.geely.com/news/1", official=list(DEFAULT_OFFICIAL_DOMAINS)) == OWNER_OURS


def test_url_live_check_disabled(monkeypatch):
    import asyncio

    from app.services.geoeval.url_live_check import SKIPPED, classify_url_liveness

    monkeypatch.setenv("CITATION_LIVE_CHECK", "false")
    out = asyncio.run(classify_url_liveness(["https://www.geely.com/a"]))
    assert out["https://www.geely.com/a"] == SKIPPED


def test_url_live_check_maps(monkeypatch):
    import asyncio

    from app.services.geoeval import url_live_check as mod

    async def fake_one(_client, url: str) -> str:
        return mod.LIVE if "geely" in url else mod.DEAD

    monkeypatch.setenv("CITATION_LIVE_CHECK", "true")
    monkeypatch.setattr(mod, "_one", fake_one)
    out = asyncio.run(
        mod.classify_url_liveness(["https://www.geely.com/a", "https://no-such-host.invalid/x"])
    )
    assert out["https://www.geely.com/a"] == mod.LIVE
    assert out["https://no-such-host.invalid/x"] == mod.DEAD


def test_schedule_uses_naive_utc():
    from pathlib import Path

    from app.services.geoflow import schedule_service as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "replace(tzinfo=None)" in src
    assert "Task.next_run_at <= now" in src or "next_run_at <= now" in src
