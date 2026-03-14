"""
查詢引擎 - 核心功能：給商家名稱，回傳最佳刷卡建議
這就是未來 Geofencing 觸發時會呼叫的邏輯
支援雙模式：有 DATABASE_URL → PostgreSQL，無 → SQLite fallback
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cards.db")
DATABASE_URL = os.getenv("DATABASE_URL")

# placeholder: PostgreSQL 用 %s，SQLite 用 ?
_PH = "%s" if DATABASE_URL else "?"


def get_conn():
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _cursor(conn):
    if DATABASE_URL:
        import psycopg2.extras
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


def _rows_to_dicts(rows):
    """統一將查詢結果轉為 list[dict]。RealDictRow 和 sqlite3.Row 都支援 dict()。"""
    return [dict(row) for row in rows]


def get_category_id_by_name(name: str) -> int | None:
    """依分類名稱取得 ID（供 brain.py / cards.py 呼叫，消除外部 raw SQL）。"""
    conn = get_conn()
    cur = _cursor(conn)
    cur.execute(f"SELECT id FROM categories WHERE name = {_PH}", (name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)["id"] if not isinstance(row, dict) else row["id"]
    return None


def recommend_by_merchant(merchant_name: str, user_card_ids: list[int] | None = None):
    """
    核心查詢：輸入商家名稱 → 回傳最佳卡片排序

    參數:
        merchant_name: 商家名稱（例如 "星巴克"）
        user_card_ids: 使用者擁有的卡片 ID 清單，None 表示不限
    回傳:
        依回饋率排序的卡片推薦清單
    """
    conn = get_conn()
    cursor = _cursor(conn)

    query = f"""
        SELECT
            c.id AS card_id,
            b.name AS bank_name,
            c.card_name,
            r.reward_type,
            r.reward_rate,
            r.reward_cap,
            r.conditions,
            cat.name AS category_name,
            m.name AS merchant_name
        FROM merchants m
        JOIN categories cat ON m.category_id = cat.id
        JOIN rewards r ON r.category_id = cat.id
        JOIN cards c ON r.card_id = c.id
        JOIN banks b ON c.bank_id = b.id
        WHERE m.name LIKE {_PH}
    """
    params = [f"%{merchant_name}%"]

    if user_card_ids:
        placeholders = ",".join([_PH] * len(user_card_ids))
        query += f" AND c.id IN ({placeholders})"
        params.extend(user_card_ids)

    query += " ORDER BY r.reward_rate DESC"

    cursor.execute(query, params)
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def recommend_by_merchants_batch(merchant_names: list[str]) -> dict[str, list[dict]]:
    """
    批次查詢多個商家的推薦卡片（一次 DB 查詢取代 N 次）。
    merchant_names 必須是精確的 DB 商家名稱（已經過 alias 對照）。
    回傳: {商家名稱: [推薦清單（依回饋率降序）]}
    """
    if not merchant_names:
        return {}

    conn = get_conn()
    cursor = _cursor(conn)

    placeholders = ",".join([_PH] * len(merchant_names))
    query = f"""
        SELECT
            c.id AS card_id,
            b.name AS bank_name,
            c.card_name,
            r.reward_type,
            r.reward_rate,
            r.reward_cap,
            r.conditions,
            cat.name AS category_name,
            m.name AS merchant_name
        FROM merchants m
        JOIN categories cat ON m.category_id = cat.id
        JOIN rewards r ON r.category_id = cat.id
        JOIN cards c ON r.card_id = c.id
        JOIN banks b ON c.bank_id = b.id
        WHERE m.name IN ({placeholders})
        ORDER BY m.name, r.reward_rate DESC
    """

    cursor.execute(query, merchant_names)

    result: dict[str, list[dict]] = {}
    for row in cursor.fetchall():
        d = dict(row)
        name = d["merchant_name"]
        if name not in result:
            result[name] = []
        result[name].append(d)

    conn.close()
    return result


def recommend_by_category(category_name: str):
    """依消費分類查詢最佳卡片"""
    conn = get_conn()
    cursor = _cursor(conn)

    cursor.execute(f"""
        SELECT
            c.id AS card_id,
            b.name AS bank_name,
            c.card_name,
            r.reward_type,
            r.reward_rate,
            r.reward_cap,
            r.conditions,
            cat.name AS category_name
        FROM rewards r
        JOIN cards c ON r.card_id = c.id
        JOIN banks b ON c.bank_id = b.id
        JOIN categories cat ON r.category_id = cat.id
        WHERE cat.name LIKE {_PH}
        ORDER BY r.reward_rate DESC
    """, (f"%{category_name}%",))

    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def list_all_cards():
    """列出所有信用卡"""
    conn = get_conn()
    cursor = _cursor(conn)
    cursor.execute("""
        SELECT c.id, b.name AS bank_name, c.card_name, c.annual_fee, c.note
        FROM cards c
        JOIN banks b ON c.bank_id = b.id
        ORDER BY b.name
    """)
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def list_categories():
    """列出所有分類（樹狀）"""
    conn = get_conn()
    cursor = _cursor(conn)
    cursor.execute("""
        SELECT
            c.id, c.name, c.parent_id,
            p.name AS parent_name
        FROM categories c
        LEFT JOIN categories p ON c.parent_id = p.id
        ORDER BY c.parent_id NULLS FIRST, c.id
    """)
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def recommend_by_category_id(category_id: int, user_card_ids: list[int] | None = None):
    """依分類 ID 查詢最佳卡片，支援使用者卡片過濾"""
    conn = get_conn()
    cursor = _cursor(conn)

    # 若傳入的是父分類，同時查其子分類
    query = f"""
        SELECT
            c.id AS card_id,
            b.name AS bank_name,
            c.card_name,
            r.reward_type,
            r.reward_rate,
            r.reward_cap,
            r.conditions,
            cat.name AS category_name
        FROM rewards r
        JOIN cards c ON r.card_id = c.id
        JOIN banks b ON c.bank_id = b.id
        JOIN categories cat ON r.category_id = cat.id
        WHERE (cat.id = {_PH} OR cat.parent_id = {_PH})
    """
    params: list = [category_id, category_id]

    if user_card_ids:
        placeholders = ",".join([_PH] * len(user_card_ids))
        query += f" AND c.id IN ({placeholders})"
        params.extend(user_card_ids)

    query += " ORDER BY r.reward_rate DESC"

    cursor.execute(query, params)
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def get_card_rewards(card_id: int):
    """列出某張卡的所有回饋規則，按回饋率排序"""
    conn = get_conn()
    cursor = _cursor(conn)
    cursor.execute(f"""
        SELECT
            r.reward_type,
            r.reward_rate,
            r.reward_cap,
            r.conditions,
            cat.id AS category_id,
            cat.name AS category_name,
            cat.parent_id,
            pcat.name AS parent_name
        FROM rewards r
        JOIN categories cat ON r.category_id = cat.id
        LEFT JOIN categories pcat ON cat.parent_id = pcat.id
        WHERE r.card_id = {_PH}
        ORDER BY r.reward_rate DESC
    """, (card_id,))
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


def search_merchants(q: str):
    """商家名稱模糊搜尋（autocomplete 用）"""
    conn = get_conn()
    cursor = _cursor(conn)
    cursor.execute(f"""
        SELECT m.id, m.name, cat.name AS category_name
        FROM merchants m
        JOIN categories cat ON m.category_id = cat.id
        WHERE m.name LIKE {_PH}
        ORDER BY m.name
        LIMIT 10
    """, (f"%{q}%",))
    results = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return results


# === 直接執行時做 Demo ===
if __name__ == "__main__":
    print("=" * 50)
    print("  信用卡推薦引擎 Demo")
    print("=" * 50)

    print("\n--- 所有信用卡 ---")
    for card in list_all_cards():
        print(f"  [{card['id']}] {card['bank_name']} {card['card_name']} - {card['note']}")

    print("\n--- 消費分類 ---")
    for cat in list_categories():
        prefix = "  └─ " if cat["parent_id"] else "📁 "
        print(f"{prefix}{cat['name']}")

    # 模擬 Geofencing 場景
    test_merchants = ["星巴克", "全家", "Uber Eats", "中油"]
    for merchant in test_merchants:
        print(f"\n--- 偵測到你在「{merchant}」，建議刷 ---")
        results = recommend_by_merchant(merchant)
        if results:
            for i, r in enumerate(results, 1):
                cap_str = f" (上限 ${r['reward_cap']}/月)" if r["reward_cap"] else ""
                cond_str = f" [{r['conditions']}]" if r["conditions"] else ""
                print(f"  {i}. {r['bank_name']} {r['card_name']} → {r['reward_rate']}% {r['reward_type']}{cap_str}{cond_str}")
        else:
            print("  (尚無匹配的回饋資料)")
