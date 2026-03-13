"""
CardBrain 3.0 精算引擎
在同一個引擎上支援三種模式：即時推薦、後悔計算機、行程規劃
核心差異：從「查回饋率」升級為「算真實省多少錢」
"""

from database.query import (
    recommend_by_merchant,
    recommend_by_category_id,
    get_conn,
)

# ── 行程規劃：消費類別 → DB 分類名稱映射 ──────────────
TRIP_CATEGORY_MAPPING = {
    "flights": "航空公司",
    "hotels": "訂房網站",
    "shopping": "海外消費",
    "dining": "餐廳",
    "transport": "大眾運輸",
}

COUNTRY_CATEGORIES = {
    "日本": "日本消費",
    "韓國": "韓國消費",
}


def calculate_reward(
    amount: float,
    reward_rate: float,
    reward_cap: float | None = None,
    reward_type: str = "cashback",
) -> float:
    """
    單筆精算：金額 * 回饋率，考慮月上限。
    回傳實際回饋金額（元）。
    """
    raw = amount * reward_rate / 100.0
    if reward_cap and raw > reward_cap:
        return reward_cap
    return round(raw, 2)


def instant_recommend(
    merchant_name: str,
    amount: float,
    user_card_ids: list[int] | None = None,
    category: str | None = None,
) -> dict:
    """
    即時推薦：給商家 + 金額，回傳按實際回饋金額排序的卡片清單。
    fallback 路徑：商家 → category 分類 → 國內一般消費
    """
    recs = recommend_by_merchant(merchant_name, user_card_ids)
    if not recs and category:
        recs = _query_by_category_name(category, user_card_ids)
    if not recs:
        recs = _fallback_general(user_card_ids)

    results = _enrich_with_actual_reward(recs, amount)
    results.sort(key=lambda x: x["actual_reward"], reverse=True)

    return {
        "merchant": merchant_name,
        "amount": amount,
        "results": results,
    }


def instant_recommend_by_category(
    category_id: int,
    amount: float,
    user_card_ids: list[int] | None = None,
) -> dict:
    """
    分類即時推薦：給分類 ID + 金額，回傳按實際回饋金額排序。
    """
    recs = recommend_by_category_id(category_id, user_card_ids)
    results = _enrich_with_actual_reward(recs, amount)
    results.sort(key=lambda x: x["actual_reward"], reverse=True)

    return {
        "category_id": category_id,
        "amount": amount,
        "results": results,
    }


def regret_calculate(
    transactions: list[dict],
    user_card_ids: list[int] | None = None,
) -> dict:
    """
    後悔計算機：多筆交易，逐筆比較「你用的卡 vs 最佳卡」。

    transactions: [{"merchant": "星巴克", "amount": 300, "card_id": 1}, ...]
    回傳：每筆的比較結果 + 總後悔金額
    """
    details = []
    total_your_reward = 0.0
    total_best_reward = 0.0

    for tx in transactions:
        merchant = tx["merchant"]
        amount = tx["amount"]
        used_card_id = tx["card_id"]

        # 查所有卡的推薦（含使用者擁有的）
        all_recs = recommend_by_merchant(merchant, user_card_ids)
        if not all_recs:
            all_recs = _fallback_general(user_card_ids)

        # 找使用者用的卡的回饋
        your_rec = next((r for r in all_recs if r["card_id"] == used_card_id), None)
        if your_rec:
            your_reward = calculate_reward(
                amount, your_rec["reward_rate"], your_rec.get("reward_cap"), your_rec["reward_type"]
            )
        else:
            your_reward = 0.0

        # 找最佳卡
        enriched = _enrich_with_actual_reward(all_recs, amount)
        enriched.sort(key=lambda x: x["actual_reward"], reverse=True)
        best = enriched[0] if enriched else None
        best_reward = best["actual_reward"] if best else 0.0

        regret = round(best_reward - your_reward, 2)
        total_your_reward += your_reward
        total_best_reward += best_reward

        detail = {
            "merchant": merchant,
            "amount": amount,
            "your_card_id": used_card_id,
            "your_reward": round(your_reward, 2),
            "best_reward": round(best_reward, 2),
            "regret": regret,
        }
        if your_rec:
            detail["your_card"] = f"{your_rec['bank_name']} {your_rec['card_name']}"
            detail["your_rate"] = your_rec["reward_rate"]
        if best:
            detail["best_card"] = f"{best['bank_name']} {best['card_name']}"
            detail["best_rate"] = best["reward_rate"]

        details.append(detail)

    total_regret = round(total_best_reward - total_your_reward, 2)
    return {
        "details": details,
        "total_your_reward": round(total_your_reward, 2),
        "total_best_reward": round(total_best_reward, 2),
        "total_regret": total_regret,
    }


def plan_trip(
    destination: str,
    total_budget: float,
    breakdown: dict[str, float] | None = None,
    user_card_ids: list[int] | None = None,
) -> dict:
    """
    行程規劃：依消費類別各自找最佳卡，加總回饋。

    destination: 旅遊目的地（如 "日本"）
    total_budget: 總預算
    breakdown: {"flights": 30000, "hotels": 25000, "shopping": 25000, "dining": 10000, "transport": 10000}
    """
    # 若無 breakdown，按預設比例拆分
    if not breakdown:
        breakdown = {
            "flights": round(total_budget * 0.30),
            "hotels": round(total_budget * 0.25),
            "shopping": round(total_budget * 0.25),
            "dining": round(total_budget * 0.10),
            "transport": round(total_budget * 0.10),
        }

    # 查詢目的地是否有對應特殊分類
    country_cat = COUNTRY_CATEGORIES.get(destination)

    category_results = []
    total_savings = 0.0
    cards_to_bring = {}  # card_name -> 用途

    for key, amount in breakdown.items():
        if amount <= 0:
            continue

        cat_name = TRIP_CATEGORY_MAPPING.get(key, "海外消費")
        cat_label = _category_label(key)

        # 先查特定分類，再嘗試國家分類
        recs = _query_by_category_name(cat_name, user_card_ids)
        if country_cat and not recs:
            recs = _query_by_category_name(country_cat, user_card_ids)
        if not recs:
            recs = _fallback_general(user_card_ids)

        enriched = _enrich_with_actual_reward(recs, amount)
        enriched.sort(key=lambda x: x["actual_reward"], reverse=True)
        best = enriched[0] if enriched else None

        savings = best["actual_reward"] if best else 0.0
        total_savings += savings

        item = {
            "category": key,
            "category_label": cat_label,
            "amount": amount,
            "savings": round(savings, 2),
        }
        if best:
            card_key = f"{best['bank_name']} {best['card_name']}"
            item["best_card"] = card_key
            item["best_rate"] = best["reward_rate"]
            # 記錄帶卡清單
            if card_key not in cards_to_bring:
                cards_to_bring[card_key] = []
            cards_to_bring[card_key].append(cat_label)

        category_results.append(item)

    return {
        "destination": destination,
        "total_budget": total_budget,
        "breakdown": category_results,
        "total_savings": round(total_savings, 2),
        "cards_to_bring": [
            {"card": card, "usage": usage}
            for card, usage in cards_to_bring.items()
        ],
    }


# ── 內部輔助函式 ─────────────────────────────────

def _enrich_with_actual_reward(recs: list[dict], amount: float) -> list[dict]:
    """為推薦結果加上 actual_reward 欄位。"""
    results = []
    seen = set()
    for r in recs:
        # 去重：同卡同分類只算一次
        key = (r["card_id"], r.get("category_name", ""))
        if key in seen:
            continue
        seen.add(key)

        actual = calculate_reward(
            amount, r["reward_rate"], r.get("reward_cap"), r["reward_type"]
        )
        item = {**r, "actual_reward": actual}
        results.append(item)
    return results


def _fallback_general(user_card_ids: list[int] | None = None) -> list[dict]:
    """查詢「國內一般消費」分類作為 fallback。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE name = '國內一般消費'")
    row = cur.fetchone()
    conn.close()
    if row:
        return recommend_by_category_id(row["id"], user_card_ids)
    return []


def _query_by_category_name(
    cat_name: str, user_card_ids: list[int] | None = None
) -> list[dict]:
    """用分類名稱查詢推薦。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return recommend_by_category_id(row["id"], user_card_ids)
    return []


def _category_label(key: str) -> str:
    """英文 key 轉中文顯示。"""
    labels = {
        "flights": "機票",
        "hotels": "住宿",
        "shopping": "購物",
        "dining": "餐飲",
        "transport": "交通",
    }
    return labels.get(key, key)
