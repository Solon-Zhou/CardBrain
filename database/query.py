"""
查詢引擎 - 核心功能：給商家名稱，回傳最佳刷卡建議
這就是未來 Geofencing 觸發時會呼叫的邏輯
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cards.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    cursor = conn.cursor()

    query = """
        SELECT
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
        WHERE m.name LIKE ?
    """
    params = [f"%{merchant_name}%"]

    if user_card_ids:
        placeholders = ",".join("?" * len(user_card_ids))
        query += f" AND c.id IN ({placeholders})"
        params.extend(user_card_ids)

    query += " ORDER BY r.reward_rate DESC"

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def recommend_by_category(category_name: str):
    """依消費分類查詢最佳卡片"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
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
        WHERE cat.name LIKE ?
        ORDER BY r.reward_rate DESC
    """, (f"%{category_name}%",))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def list_all_cards():
    """列出所有信用卡"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, b.name AS bank_name, c.card_name, c.annual_fee, c.note
        FROM cards c
        JOIN banks b ON c.bank_id = b.id
        ORDER BY b.name
    """)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def list_categories():
    """列出所有分類（樹狀）"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id, c.name, c.parent_id,
            p.name AS parent_name
        FROM categories c
        LEFT JOIN categories p ON c.parent_id = p.id
        ORDER BY c.parent_id NULLS FIRST, c.id
    """)
    results = [dict(row) for row in cursor.fetchall()]
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
