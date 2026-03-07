"""
CardBrain PWA — FastAPI 後端
同時 serve API + 靜態前端
"""

import json
import math
import time
import urllib.request
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from fastapi import Request

from database.query import (
    list_all_cards,
    list_categories,
    recommend_by_merchant,
    recommend_by_category_id,
    search_merchants,
)
from database.merchant_aliases import match_osm_to_merchant
from brain import (
    instant_recommend,
    instant_recommend_by_category,
    regret_calculate,
    plan_trip,
)
from llm import extract_intent

app = FastAPI(title="CardBrain API")

BASE = Path(__file__).parent

# ── Nearby cache（5 分鐘 TTL）────────────────────────
_nearby_cache: dict[str, tuple[float, list]] = {}
_NEARBY_TTL = 300  # seconds


# ── API ──────────────────────────────────────────────

@app.get("/api/cards")
def api_cards():
    return list_all_cards()


@app.get("/api/categories")
def api_categories():
    """回傳巢狀分類結構"""
    flat = list_categories()
    parents = [c for c in flat if c["parent_id"] is None]
    children = [c for c in flat if c["parent_id"] is not None]

    result = []
    for p in parents:
        p["children"] = [c for c in children if c["parent_id"] == p["id"]]
        result.append(p)
    return result


@app.get("/api/recommend/merchant")
def api_recommend_merchant(
    q: str = Query(..., min_length=1),
    card_ids: str = Query(""),
):
    ids = _parse_ids(card_ids)
    results = recommend_by_merchant(q, ids or None)

    # fallback：若商家無匹配，查「國內一般消費」分類
    if not results:
        from database.query import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM categories WHERE name = '國內一般消費'")
        row = cur.fetchone()
        conn.close()
        if row:
            results = recommend_by_category_id(row["id"], ids or None)

    return results


@app.get("/api/recommend/category")
def api_recommend_category(
    category_id: int = Query(...),
    card_ids: str = Query(""),
):
    ids = _parse_ids(card_ids)
    return recommend_by_category_id(category_id, ids or None)


@app.get("/api/merchants/search")
def api_merchants_search(q: str = Query(..., min_length=1)):
    return search_merchants(q)


@app.post("/api/brain")
async def api_brain(request: Request):
    """
    CardBrain 3.0 精算端點。
    接受 {mode, query, merchant, amount, card_ids, transactions, destination, budget, breakdown}
    """
    body = await request.json()
    mode = body.get("mode")
    query = body.get("query")
    card_ids = body.get("card_ids")

    # 若有自然語言 query，經過意圖萃取補齊 merchant/amount 等欄位
    if query:
        intent = extract_intent(query)
        # 合併 intent 到 body（body 中已有的欄位優先）
        for k, v in intent.items():
            if k not in body or body[k] is None:
                body[k] = v
        if not mode:
            mode = body.get("mode", "instant")

    if mode == "instant":
        return _handle_instant(body, card_ids)
    elif mode == "regret":
        return _handle_regret(body, card_ids)
    elif mode == "plan":
        return _handle_plan(body, card_ids)
    else:
        return {"error": "Unknown mode. Use: instant, regret, plan"}


def _handle_instant(body: dict, card_ids: list[int] | None) -> dict:
    merchant = body.get("merchant")
    amount = body.get("amount", 0)
    category_id = body.get("category_id")

    if not amount:
        return {"error": "amount is required for instant mode"}

    if category_id:
        return instant_recommend_by_category(category_id, float(amount), card_ids)
    elif merchant:
        return instant_recommend(merchant, float(amount), card_ids)
    else:
        return {"error": "merchant or category_id is required"}


def _handle_regret(body: dict, card_ids: list[int] | None) -> dict:
    transactions = body.get("transactions", [])
    if not transactions:
        return {"error": "transactions is required for regret mode"}
    return regret_calculate(transactions, card_ids)


def _handle_plan(body: dict, card_ids: list[int] | None) -> dict:
    destination = body.get("destination", "")
    budget = body.get("budget", 0)
    breakdown = body.get("breakdown")

    if not destination:
        return {"error": "destination is required for plan mode"}
    if not budget and not breakdown:
        return {"error": "budget or breakdown is required for plan mode"}

    return plan_trip(destination, float(budget), breakdown, card_ids)


@app.get("/api/nearby")
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

    # 呼叫 Overpass API
    pois = _query_overpass(actual_lat, actual_lng)

    # 匹配 + 去重
    seen_merchants: set[str] = set()
    matched: list[dict] = []
    for poi in pois:
        tags = poi.get("tags", {})
        osm_name = tags.get("name", "")
        osm_brand = tags.get("brand", "")
        if not osm_name and not osm_brand:
            continue
        merchant_name = match_osm_to_merchant(osm_name, osm_brand)
        if not merchant_name or merchant_name in seen_merchants:
            continue
        seen_merchants.add(merchant_name)

        # 計算距離
        poi_lat = poi.get("lat", poi.get("center", {}).get("lat", 0))
        poi_lng = poi.get("lon", poi.get("center", {}).get("lon", 0))
        dist = _haversine(actual_lat, actual_lng, poi_lat, poi_lng)

        # 查推薦卡片（不帶 user_card_ids，cache 全部結果）
        recs = recommend_by_merchant(merchant_name)
        if not recs:
            continue
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

    # 寫入 cache
    _nearby_cache[cache_key] = (now, matched)

    return _filter_nearby(matched, card_ids, actual_lat, actual_lng)


def _filter_nearby(matched: list[dict], card_ids: str, user_lat: float, user_lng: float) -> dict:
    """根據使用者卡片過濾 top_card，回傳精簡結果。"""
    ids = _parse_ids(card_ids)
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


def _query_overpass(lat: float, lng: float) -> list[dict]:
    """呼叫 Overpass API 查附近 500m 的商業 POI。"""
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
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("elements", [])
    except Exception:
        return []


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 公式計算兩點距離（公尺）。"""
    R = 6371000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── 靜態檔 + SPA fallback ────────────────────────────

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

_index_html = (BASE / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str = ""):
    return _index_html


# ── helpers ──────────────────────────────────────────

def _parse_ids(s: str) -> list[int]:
    if not s.strip():
        return []
    return [int(x) for x in s.split(",") if x.strip().isdigit()]
