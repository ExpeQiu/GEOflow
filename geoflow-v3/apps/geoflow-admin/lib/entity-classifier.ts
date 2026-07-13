/** 品牌与产品实体分类（与后端 entity_classifier.py 规则对齐） */

const PRODUCT_MARKERS = [
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
];

const PURE_BRAND_NAMES = new Set([
  "吉利汽车", "吉利", "比亚迪", "理想汽车", "理想", "小鹏汽车", "小鹏",
  "蔚来汽车", "蔚来", "特斯拉", "长安汽车", "长安", "奇瑞汽车", "奇瑞",
  "问界", "智界", "尊界", "华为", "小米汽车", "小米", "阿维塔", "智己",
  "极氪", "领克", "零跑", "哪吒", "上汽", "广汽", "长城汽车", "长城",
]);

function hasProductMarker(text: string): boolean {
  const upper = text.toUpperCase();
  return PRODUCT_MARKERS.some((m) => upper.includes(m.toUpperCase()) || text.includes(m));
}

export function inferEntityType(name: string): "brand" | "product" {
  const text = (name || "").trim();
  if (!text) return "brand";
  if (hasProductMarker(text)) return "product";
  if (/[\s　]/.test(text)) {
    const tail = text.split(/[\s　]+/).slice(1).join(" ");
    if (tail && hasProductMarker(tail)) return "product";
  }
  if (text.endsWith("汽车")) return "brand";
  if (PURE_BRAND_NAMES.has(text)) return "brand";
  if (/[A-Za-z]/.test(text)) return "product";
  if (text.length <= 4 && text.endsWith("界")) return "brand";
  return "brand";
}

export function isProductName(name: string): boolean {
  return inferEntityType(name) === "product";
}
