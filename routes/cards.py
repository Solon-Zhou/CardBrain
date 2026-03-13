# routes/cards.py — 卡片 / 分類 / 商家查詢
from fastapi import APIRouter, Query
from database.query import (
    list_all_cards,
    list_categories,
    recommend_by_merchant,
    recommend_by_category_id,
    get_card_rewards,
    search_merchants,
)
from routes import parse_ids

router = APIRouter()


@router.get("/api/cards")
def api_cards():
    return list_all_cards()


@router.get("/api/categories")
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


@router.get("/api/recommend/merchant")
def api_recommend_merchant(
    q: str = Query(..., min_length=1),
    card_ids: str = Query(""),
):
    ids = parse_ids(card_ids)
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


@router.get("/api/recommend/category")
def api_recommend_category(
    category_id: int = Query(...),
    card_ids: str = Query(""),
):
    ids = parse_ids(card_ids)
    return recommend_by_category_id(category_id, ids or None)


@router.get("/api/cards/{card_id}/rewards")
def api_card_rewards(card_id: int):
    """取得某張卡的所有回饋規則"""
    return get_card_rewards(card_id)


@router.get("/api/merchants/search")
def api_merchants_search(q: str = Query(..., min_length=1)):
    return search_merchants(q)
