"""品牌与产品实体分类 — 矩阵与竞品配置的语义隔离。"""

import logging
import re

logger = logging.getLogger(__name__)

# 智驾系统 / 产品技术标识
_PRODUCT_MARKERS = (
    "ADS",
    "AD MAX",
    "AD PRO",
    " FSD",
    "XNGP",
    "NOP+",
    "NOP ",
    "DIPILOT",
    "IM AD",
    "AVATARDRIVE",
    "G-ASD",
    "千里浩瀚",
    "浩瀚",
    "PILOT",
    "智驾",
    "辅助驾驶",
    "AUTOPILOT",
    "NOA",
    " NGP",
)

# 无产品后缀时的纯品牌名
_PURE_BRAND_NAMES = frozenset(
    {
        "吉利汽车",
        "吉利",
        "比亚迪",
        "理想汽车",
        "理想",
        "小鹏汽车",
        "小鹏",
        "蔚来汽车",
        "蔚来",
        "特斯拉",
        "长安汽车",
        "长安",
        "奇瑞汽车",
        "奇瑞",
        "问界",
        "智界",
        "尊界",
        "华为",
        "小米汽车",
        "小米",
        "阿维塔",
        "智己",
        "极氪",
        "领克",
        "零跑",
        "哪吒",
        "上汽",
        "广汽",
        "长城汽车",
        "长城",
    }
)


def _has_product_marker(text: str) -> bool:
    upper = text.upper()
    return any(marker.upper() in upper or marker in text for marker in _PRODUCT_MARKERS)


def infer_entity_type(name: str) -> str:
    """推断实体类型：brand（品牌）或 product（产品/智驾系统）。"""
    text = (name or "").strip()
    if not text:
        return "brand"

    if _has_product_marker(text):
        return "product"

    # 「品牌名 + 产品名」如：吉利汽车 千里浩瀚G-ASD
    if re.search(r"[\s　]", text):
        parts = re.split(r"[\s　]+", text, maxsplit=1)
        if len(parts) == 2 and _has_product_marker(parts[1]):
            return "product"

    if text.endswith("汽车"):
        return "brand"

    if text in _PURE_BRAND_NAMES:
        return "brand"

    # 含英文字母的多为产品/系统名（XNGP、DiPilot、FSD 等）
    if re.search(r"[A-Za-z]", text):
        return "product"

    if len(text) <= 4 and text.endswith("界"):
        return "brand"

    return "brand"


def filter_matrix_by_entity(matrix: list[dict], entity_type: str) -> list[dict]:
    """按实体类型过滤竞品矩阵中的条目。"""
    result: list[dict] = []
    dropped: list[str] = []
    for row in matrix:
        brands = []
        for item in row.get("brands") or []:
            name = str(item.get("name") or "")
            inferred = infer_entity_type(name)
            if inferred == entity_type:
                brands.append(item)
            elif name:
                dropped.append(name)
        if brands:
            result.append({**row, "brands": brands})
    if dropped:
        unique = sorted(set(dropped))
        logger.info("matrix_entity_filtered target=%s dropped=%s", entity_type, unique[:20])
    return result


def matrix_competitor_names(matrix: list[dict]) -> list[str]:
    names: list[str] = []
    for row in matrix:
        for item in row.get("brands") or []:
            name = str(item.get("name") or "")
            if name and name not in names:
                names.append(name)
    return names
