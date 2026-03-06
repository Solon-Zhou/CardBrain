"""
CardBrain PWA — FastAPI 後端
同時 serve API + 靜態前端
"""

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from database.query import (
    list_all_cards,
    list_categories,
    recommend_by_merchant,
    recommend_by_category_id,
    search_merchants,
)

app = FastAPI(title="CardBrain API")

BASE = Path(__file__).parent


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
