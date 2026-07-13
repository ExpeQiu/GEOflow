from app.services.geoeval.entity_classifier import filter_matrix_by_entity, infer_entity_type


def test_brand_names():
    assert infer_entity_type("吉利汽车") == "brand"
    assert infer_entity_type("理想汽车") == "brand"
    assert infer_entity_type("蔚来汽车") == "brand"
    assert infer_entity_type("比亚迪") == "brand"
    assert infer_entity_type("问界") == "brand"
    assert infer_entity_type("特斯拉") == "brand"


def test_product_names():
    assert infer_entity_type("华为 ADS") == "product"
    assert infer_entity_type("特斯拉 FSD") == "product"
    assert infer_entity_type("吉利汽车 千里浩瀚G-ASD") == "product"
    assert infer_entity_type("小鹏 XNGP") == "product"
    assert infer_entity_type("理想AD Max") == "product"
    assert infer_entity_type("蔚来 NOP+") == "product"
    assert infer_entity_type("比亚迪 DiPilot") == "product"
    assert infer_entity_type("智己IM AD") == "product"
    assert infer_entity_type("阿维塔 AvatarDrive") == "product"


def test_filter_product_matrix():
    matrix = [
        {
            "platform": "doubao",
            "brands": [
                {"name": "吉利汽车", "visibility_pct": 10, "is_self": False},
                {"name": "小鹏 XNGP", "visibility_pct": 70, "is_self": False},
                {"name": "华为 ADS", "visibility_pct": 73.3, "is_self": False},
            ],
        }
    ]
    filtered = filter_matrix_by_entity(matrix, "product")
    names = [b["name"] for b in filtered[0]["brands"]]
    assert names == ["小鹏 XNGP", "华为 ADS"]


def test_filter_brand_matrix():
    matrix = [
        {
            "platform": "doubao",
            "brands": [
                {"name": "吉利汽车", "visibility_pct": 10, "is_self": True},
                {"name": "小鹏 XNGP", "visibility_pct": 70, "is_self": False},
            ],
        }
    ]
    filtered = filter_matrix_by_entity(matrix, "brand")
    names = [b["name"] for b in filtered[0]["brands"]]
    assert names == ["吉利汽车"]
