"""
商家名稱對照表 — OSM (Overpass API) 名稱 → DB 商家名稱
OSM 的 POI name/brand 格式多樣，需要對照到 merchants 表中的 46 家商家。
"""


# key: OSM 可能出現的名稱（全小寫）, value: DB merchants.name
MERCHANT_ALIASES = {
    # 咖啡店
    "starbucks": "星巴克",
    "星巴克": "星巴克",
    "統一星巴克": "星巴克",
    "louisa coffee": "路易莎",
    "louisa": "路易莎",
    "路易莎": "路易莎",
    "路易莎咖啡": "路易莎",
    "cama café": "cama cafe",
    "cama cafe": "cama cafe",
    "cama": "cama cafe",
    # 超商
    "7-eleven": "7-ELEVEN",
    "seven eleven": "7-ELEVEN",
    "7-11": "7-ELEVEN",
    "7-Eleven": "7-ELEVEN",
    "統一超商": "7-ELEVEN",
    "familymart": "全家便利商店",
    "family mart": "全家便利商店",
    "全家": "全家便利商店",
    "全家便利商店": "全家便利商店",
    "hi-life": "萊爾富",
    "hilife": "萊爾富",
    "萊爾富": "萊爾富",
    "ok超商": "OK超商",
    "ok mart": "OK超商",
    "okmart": "OK超商",
    # 超市
    "全聯": "全聯",
    "全聯福利中心": "全聯",
    "pxmart": "全聯",
    "美廉社": "美廉社",
    "simple mart": "美廉社",
    # 量販店
    "carrefour": "家樂福",
    "家樂福": "家樂福",
    "costco": "好市多 Costco",
    "好市多": "好市多 Costco",
    "大潤發": "大潤發",
    "rt-mart": "大潤發",
    # 速食
    "mcdonald's": "麥當勞",
    "mcdonalds": "麥當勞",
    "mcdonald": "麥當勞",
    "麥當勞": "麥當勞",
    "kfc": "肯德基",
    "肯德基": "肯德基",
    "mos burger": "摩斯漢堡",
    "摩斯漢堡": "摩斯漢堡",
    "摩斯": "摩斯漢堡",
    "burger king": "漢堡王",
    "漢堡王": "漢堡王",
    # 外送平台
    "uber eats": "Uber Eats",
    "foodpanda": "foodpanda",
    # 餐廳
    "王品": "王品集團",
    "王品集團": "王品集團",
    "din tai fung": "鼎泰豐",
    "鼎泰豐": "鼎泰豐",
    "瓦城": "瓦城",
    "瓦城泰統": "瓦城",
    "築間": "築間",
    "築間幸福鍋物": "築間",
    # 早餐店
    "麥味登": "麥味登",
    "拉亞漢堡": "拉亞漢堡",
    "拉亞": "拉亞漢堡",
    # 百貨公司
    "新光三越": "新光三越",
    "shin kong mitsukoshi": "新光三越",
    "sogo": "SOGO",
    "太平洋sogo": "SOGO",
    "太平洋崇光": "SOGO",
    "微風廣場": "微風廣場",
    "微風": "微風廣場",
    "breeze center": "微風廣場",
    "遠東百貨": "遠東百貨",
    "far eastern": "遠東百貨",
    # 加油
    "中油": "中油",
    "中國石油": "中油",
    "cpc": "中油",
    "台塑": "台塑",
    "台塑石油": "台塑",
    "formosa petrochemical": "台塑",
    # 大眾運輸
    "台北捷運": "台北捷運",
    "taipei metro": "台北捷運",
    "台灣高鐵": "台灣高鐵",
    "thsr": "台灣高鐵",
    "台鐵": "台鐵",
    "tra": "台鐵",
    # 藥妝
    "watsons": "屈臣氏",
    "屈臣氏": "屈臣氏",
    "cosmed": "康是美",
    "康是美": "康是美",
}


def match_osm_to_merchant(osm_name: str, osm_brand: str = "") -> str | None:
    """
    將 OSM POI 的 name/brand 匹配到 DB 的 merchants.name。

    策略：
    1. 精確匹配（name 或 brand 直接在對照表中）
    2. 包含匹配（對照表的 key 出現在 name/brand 中）

    回傳: 匹配到的 DB 商家名稱，或 None
    """
    name_lower = osm_name.lower().strip()
    brand_lower = osm_brand.lower().strip()

    # 1) 精確匹配
    if name_lower in MERCHANT_ALIASES:
        return MERCHANT_ALIASES[name_lower]
    if brand_lower and brand_lower in MERCHANT_ALIASES:
        return MERCHANT_ALIASES[brand_lower]

    # 2) 包含匹配：對照表 key 是否為 name/brand 的子字串
    for alias, merchant_name in MERCHANT_ALIASES.items():
        if alias in name_lower or (brand_lower and alias in brand_lower):
            return merchant_name

    return None
