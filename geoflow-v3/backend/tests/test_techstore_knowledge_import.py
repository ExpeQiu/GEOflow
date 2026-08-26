"""Techstore → GEOFlow 知识库 / 技术 IP 导入算子。"""

from app.services.admin.techstore_snapshot import (
    build_kb_payloads,
    build_tech_asset_rows,
    load_fixture_snapshot,
    preview_from_snapshot,
    wiki_slug_from_url,
)


def test_wiki_slug_from_url():
    assert wiki_slug_from_url("/concepts/g-ads") == "g-ads"
    assert wiki_slug_from_url("https://tech.geely.com/concepts/shen-dun-battery.mdx") == "shen-dun-battery"
    assert wiki_slug_from_url("") == ""


def test_fixture_splits_by_domain_and_skips_draft():
    snap = load_fixture_snapshot()
    kbs = {p["name"]: p["content"] for p in build_kb_payloads(snap)}
    assert "Geely/智能驾驶" in kbs
    assert "Geely/三电安全" in kbs
    assert "Geely/FAQ" in kbs
    assert "Geely/门店" in kbs
    assert "SECRET_SHOULD_NOT_IMPORT" not in "".join(kbs.values())
    assert "GEELY_KB_FACT_SHIELD_420" in kbs["Geely/三电安全"]
    assert "G-ADS 不是 L3" in kbs["Geely/智能驾驶"]
    assert "智能驾驶辅助" in kbs["Geely/FAQ"]


def test_fixture_tech_assets_use_wiki_slug_as_ip():
    snap = load_fixture_snapshot()
    rows = build_tech_asset_rows(snap)
    by_id = {r["ip_id"]: r for r in rows}
    assert set(by_id) == {"g-ads", "sea-architecture", "shen-dun-battery"}
    assert by_id["g-ads"]["wiki_slug"] == "g-ads"
    assert by_id["g-ads"]["mind_tag"] == "智能驾驶"
    assert by_id["shen-dun-battery"]["mind_tag"] == "三电安全"
    assert by_id["g-ads"]["ip_layer"] == "L1"


def test_preview_counts_exclude_draft_docs():
    snap = load_fixture_snapshot()
    preview = preview_from_snapshot(snap)
    assert preview["source"] == "fixture"
    assert preview["connected"] is False
    assert preview["counts"]["documents"] == 1
    assert preview["counts"]["techniques"] == 3
    assert preview["asset_count"] == 3
    assert "Geely/FAQ" in preview["kb_names"]
