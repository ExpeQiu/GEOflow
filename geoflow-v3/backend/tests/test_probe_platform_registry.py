"""自定义被监测平台注册表测试。"""

from app.services.geoeval.probe_platform_registry import (
    merged_platform_meta,
    normalize_custom_platform,
    parse_custom_platforms,
    platform_order,
)


def test_normalize_custom_platform_ok():
    row = normalize_custom_platform(
        {
            "id": "zhipu",
            "label": "智谱清言",
            "api_capable": True,
            "default_model": "glm-4",
            "default_base": "https://open.bigmodel.cn/api/paas/v4",
        }
    )
    assert row is not None
    assert row["id"] == "zhipu"
    assert row["custom"] is True


def test_normalize_rejects_builtin_id():
    assert normalize_custom_platform({"id": "doubao", "label": "假豆包"}) is None


def test_normalize_rejects_invalid_id():
    assert normalize_custom_platform({"id": "1bad", "label": "x"}) is None
    assert normalize_custom_platform({"id": "", "label": "x"}) is None


def test_merged_platform_meta_includes_custom():
    cfg = {
        "custom_platforms": [
            {"id": "zhipu", "label": "智谱", "api_capable": True, "default_model": "glm-4"},
        ]
    }
    meta = merged_platform_meta(cfg)
    assert "zhipu" in meta
    assert meta["zhipu"]["label"] == "智谱"
    assert meta["zhipu"]["custom"] is True
    assert "doubao" in meta


def test_platform_order_builtin_then_custom():
    cfg = {"custom_platforms": [{"id": "zhipu", "label": "智谱"}]}
    order = platform_order(cfg)
    assert order.index("doubao") < order.index("zhipu")
    assert "zhipu" in order


def test_parse_custom_platforms_dedup():
    cfg = {
        "custom_platforms": [
            {"id": "zhipu", "label": "智谱"},
            {"id": "zhipu", "label": "重复"},
            {"id": "bad id", "label": "无效"},
        ]
    }
    items = parse_custom_platforms(cfg)
    assert len(items) == 1
    assert items[0]["label"] == "智谱"
