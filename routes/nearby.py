# routes/nearby.py — 附近商家
import json
import logging
import math
import os
import time
import ssl
import urllib.request
import urllib.parse
import warnings

from fastapi import APIRouter, Query
from database.query import recommend_by_merchants_batch
from database.merchant_aliases import match_osm_to_merchant
from routes import parse_ids

router = APIRouter()

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

# SSL context for outgoing HTTPS (fixes local CA issues)
try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    warnings.warn("certifi not available, using default SSL context")
    _SSL_CONTEXT = ssl.create_default_context()

# ── Nearby cache（5 分鐘 TTL，上限 100 條目）─────────
_nearby_cache: dict[str, tuple[float, list]] = {}
_NEARBY_TTL = 300  # seconds
_NEARBY_CACHE_MAX = 100


@router.get("/api/nearby")
def api_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    card_ids: str = Query(""),
    debug_lat: float | None = Query(None),
    debug_lng: float | None = Query(None),
):
    """
    偵測附近商家 + 推薦最佳卡片。
    呼叫 Overpass API 查附近 500m POI，匹配 DB 商家後回傳推薦。
    支援 debug_lat/debug_lng 模擬位置（Demo 用）。
    """
    actual_lat = debug_lat if debug_lat is not None else lat
    actual_lng = debug_lng if debug_lng is not None else lng

    # 座標四捨五入到小數 3 位作為 cache key
    cache_key = f"{round(actual_lat, 3)},{round(actual_lng, 3)}"
    now = time.time()
    if cache_key in _nearby_cache:
        cached_time, cached_data = _nearby_cache[cache_key]
        if now - cached_time < _NEARBY_TTL:
            return _filter_nearby(cached_data, card_ids, actual_lat, actual_lng)

    # 呼叫 Google Places API（fallback: Overpass）
    pois = _query_nearby_places(actual_lat, actual_lng)

    # Phase 1: 匹配 POI → DB 商家名稱，收集去重後的商家清單
    poi_merchants: list[dict] = []  # [{poi, merchant_name}]
    seen_merchants: set[str] = set()
    for poi in pois:
        poi_name = poi.get("name", "")
        if not poi_name:
            continue
        merchant_name = match_osm_to_merchant(poi_name)
        if not merchant_name or merchant_name in seen_merchants:
            continue
        seen_merchants.add(merchant_name)
        poi_merchants.append({"poi": poi, "merchant_name": merchant_name})

    # Phase 2: 一次批次查詢所有商家的推薦（取代 N+1）
    all_merchant_names = [pm["merchant_name"] for pm in poi_merchants]
    recs_map = recommend_by_merchants_batch(all_merchant_names)

    # Phase 3: 組裝結果
    matched: list[dict] = []
    for pm in poi_merchants:
        merchant_name = pm["merchant_name"]
        recs = recs_map.get(merchant_name, [])
        if not recs:
            continue
        poi = pm["poi"]
        poi_lat = poi.get("lat", 0)
        poi_lng = poi.get("lng", 0)
        dist = _haversine(actual_lat, actual_lng, poi_lat, poi_lng)
        top = recs[0]
        matched.append({
            "merchant_name": merchant_name,
            "category_name": top.get("category_name", ""),
            "distance_m": round(dist),
            "lat": poi_lat,
            "lng": poi_lng,
            "top_card": {
                "bank_name": top["bank_name"],
                "card_name": top["card_name"],
                "reward_rate": top["reward_rate"],
                "reward_type": top["reward_type"],
                "conditions": top.get("conditions", ""),
            },
            "all_recs": recs,
        })

    # 按距離排序
    matched.sort(key=lambda x: x["distance_m"])

    # 寫入 cache（先清理過期條目，超過上限則全部清空）
    expired = [k for k, (t, _) in _nearby_cache.items() if now - t >= _NEARBY_TTL]
    for k in expired:
        del _nearby_cache[k]
    if len(_nearby_cache) >= _NEARBY_CACHE_MAX:
        _nearby_cache.clear()
    _nearby_cache[cache_key] = (now, matched)

    return _filter_nearby(matched, card_ids, actual_lat, actual_lng)


def _filter_nearby(matched: list[dict], card_ids: str, user_lat: float, user_lng: float) -> dict:
    """根據使用者卡片過濾 top_card，回傳精簡結果。"""
    ids = parse_ids(card_ids)
    result = []
    for item in matched:
        top = item["top_card"]
        # 若使用者有指定卡片，找使用者擁有的最佳卡
        if ids:
            user_recs = [r for r in item["all_recs"] if r["card_id"] in ids]
            if user_recs:
                best = user_recs[0]
                top = {
                    "bank_name": best["bank_name"],
                    "card_name": best["card_name"],
                    "reward_rate": best["reward_rate"],
                    "reward_type": best["reward_type"],
                    "conditions": best.get("conditions", ""),
                }
        result.append({
            "merchant_name": item["merchant_name"],
            "category_name": item["category_name"],
            "distance_m": item["distance_m"],
            "lat": item["lat"],
            "lng": item["lng"],
            "top_card": top,
        })
    return {"user_lat": user_lat, "user_lng": user_lng, "nearby": result}


def _query_nearby_places(lat: float, lng: float) -> list[dict]:
    """查附近 500m 商業 POI。優先 Google Places API，fallback Overpass。"""
    if GOOGLE_PLACES_API_KEY:
        result = _query_google_places(lat, lng)
        if result:
            return result
    return _query_overpass(lat, lng)


def _query_google_places(lat: float, lng: float) -> list[dict]:
    """呼叫 Google Places API (New) Nearby Search。"""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = json.dumps({
        "includedTypes": [
            "restaurant", "cafe", "fast_food_restaurant",
            "convenience_store", "supermarket", "grocery_store",
            "department_store", "shopping_mall",
            "gas_station", "drugstore",
        ],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 500.0,
            }
        },
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Goog-Api-Key", GOOGLE_PLACES_API_KEY)
        req.add_header("X-Goog-FieldMask", "places.displayName,places.location")
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            places = body.get("places", [])
            return [
                {
                    "name": p.get("displayName", {}).get("text", ""),
                    "lat": p.get("location", {}).get("latitude", 0),
                    "lng": p.get("location", {}).get("longitude", 0),
                }
                for p in places
            ]
    except Exception as e:
        logging.warning("Google Places API error: %s", e)
        return []


def _query_overpass(lat: float, lng: float) -> list[dict]:
    """Fallback: 呼叫 Overpass API 查附近 500m 的商業 POI。"""
    query = f"""[out:json][timeout:10];
(
  node["shop"](around:500,{lat},{lng});
  node["amenity"~"cafe|restaurant|fast_food|fuel"](around:500,{lat},{lng});
  node["brand"](around:500,{lat},{lng});
);
out center tags;"""
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("User-Agent", "CardBrain/1.0")
        with urllib.request.urlopen(req, timeout=12, context=_SSL_CONTEXT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            # 轉為統一格式
            elements = body.get("elements", [])
            return [
                {
                    "name": e.get("tags", {}).get("name", "") or e.get("tags", {}).get("brand", ""),
                    "lat": e.get("lat", e.get("center", {}).get("lat", 0)),
                    "lng": e.get("lon", e.get("center", {}).get("lon", 0)),
                }
                for e in elements
            ]
    except Exception as e:
        logging.warning("Overpass API error: %s", e)
        return []


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 公式計算兩點距離（公尺）。"""
    R = 6371000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
