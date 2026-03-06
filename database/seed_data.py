"""
種子資料 - 先塞幾張熱門卡 + 分類，讓系統能跑起來
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cards.db")


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # === 銀行 ===
    banks = [
        ("國泰世華",),
        ("中國信託",),
        ("玉山銀行",),
        ("台新銀行",),
        ("永豐銀行",),
        ("富邦銀行",),
        ("聯邦銀行",),
        ("滙豐銀行",),
    ]
    cursor.executemany("INSERT OR IGNORE INTO banks (name) VALUES (?)", banks)

    # === 消費分類（參考 iCard.AI 結構）===
    main_categories = [
        (None, "常用消費", "shopping-cart"),
        (None, "繳費與紅利", "receipt"),
        (None, "百貨購物", "shopping-bag"),
        (None, "餐飲外送", "utensils"),
        (None, "通勤交通", "car"),
        (None, "娛樂休閒", "gamepad"),
        (None, "旅遊住宿", "plane"),
        (None, "其他", "ellipsis"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO categories (parent_id, name, icon) VALUES (?, ?, ?)",
        main_categories,
    )

    # 取得主分類 ID
    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    cat_map = {name: cid for cid, name in cursor.fetchall()}

    # 子分類
    sub_categories = [
        # 常用消費
        (cat_map["常用消費"], "國內一般消費", None),
        (cat_map["常用消費"], "海外消費", None),
        (cat_map["常用消費"], "網購", None),
        (cat_map["常用消費"], "行動支付", None),
        (cat_map["常用消費"], "超商", None),
        (cat_map["常用消費"], "超市", None),
        (cat_map["常用消費"], "量販店", None),
        # 餐飲外送
        (cat_map["餐飲外送"], "咖啡店", None),
        (cat_map["餐飲外送"], "速食", None),
        (cat_map["餐飲外送"], "外送平台", None),
        (cat_map["餐飲外送"], "餐廳", None),
        # 通勤交通
        (cat_map["通勤交通"], "加油", None),
        (cat_map["通勤交通"], "停車", None),
        (cat_map["通勤交通"], "大眾運輸", None),
        (cat_map["通勤交通"], "ETC", None),
        # 旅遊住宿
        (cat_map["旅遊住宿"], "訂房網站", None),
        (cat_map["旅遊住宿"], "航空公司", None),
        (cat_map["旅遊住宿"], "旅行社", None),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO categories (parent_id, name, icon) VALUES (?, ?, ?)",
        sub_categories,
    )

    # === 信用卡（Top 熱門卡）===
    # 先取 bank id
    cursor.execute("SELECT id, name FROM banks")
    bank_map = {name: bid for bid, name in cursor.fetchall()}

    cards = [
        (bank_map["國泰世華"], "CUBE 卡", None, 0, "熱門神卡，多通路高回饋"),
        (bank_map["中國信託"], "LINE Pay 卡", None, 0, "LINE Points 回饋"),
        (bank_map["玉山銀行"], "U Bear 卡", None, 0, "網購/超商/外送回饋"),
        (bank_map["台新銀行"], "FlyGo 卡", None, 0, "海外消費首選"),
        (bank_map["永豐銀行"], "DAWHO 現金回饋卡", None, 0, "國內外消費回饋"),
        (bank_map["富邦銀行"], "J 卡", None, 0, "日韓旅遊神卡"),
        (bank_map["聯邦銀行"], "賴點卡", None, 0, "LINE Points 回饋"),
        (bank_map["滙豐銀行"], "匯鑽卡", None, 0, "高回饋無腦刷"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO cards (bank_id, card_name, image_url, annual_fee, note) VALUES (?, ?, ?, ?, ?)",
        cards,
    )

    # === 回饋規則（示範資料）===
    cursor.execute("SELECT id, card_name FROM cards")
    card_map = {name: cid for cid, name in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NOT NULL")
    subcat_map = {name: cid for cid, name in cursor.fetchall()}

    rewards = [
        # 國泰 CUBE 卡
        (card_map["CUBE 卡"], subcat_map["咖啡店"], "cashback", 3.0, 300, "指定通路", None, None),
        (card_map["CUBE 卡"], subcat_map["網購"], "cashback", 3.0, 300, "指定通路", None, None),
        (card_map["CUBE 卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None, None, None),
        (card_map["CUBE 卡"], subcat_map["外送平台"], "cashback", 3.0, 300, "指定通路", None, None),
        # 中信 LINE Pay 卡
        (card_map["LINE Pay 卡"], subcat_map["國內一般消費"], "points", 1.0, None, None, None, None),
        (card_map["LINE Pay 卡"], subcat_map["行動支付"], "points", 3.0, None, "LINE Pay 綁定", None, None),
        # 玉山 U Bear
        (card_map["U Bear 卡"], subcat_map["網購"], "cashback", 5.0, 500, "指定平台", None, None),
        (card_map["U Bear 卡"], subcat_map["超商"], "cashback", 5.0, 500, None, None, None),
        (card_map["U Bear 卡"], subcat_map["外送平台"], "cashback", 5.0, 500, None, None, None),
        # 台新 FlyGo
        (card_map["FlyGo 卡"], subcat_map["海外消費"], "cashback", 5.0, None, None, None, None),
        (card_map["FlyGo 卡"], subcat_map["訂房網站"], "cashback", 5.0, None, None, None, None),
        (card_map["FlyGo 卡"], subcat_map["航空公司"], "cashback", 5.0, None, None, None, None),
        # 永豐 DAWHO
        (card_map["DAWHO 現金回饋卡"], subcat_map["國內一般消費"], "cashback", 2.0, None, "數位帳戶", None, None),
        (card_map["DAWHO 現金回饋卡"], subcat_map["海外消費"], "cashback", 3.0, None, None, None, None),
        # 滙豐匯鑽卡
        (card_map["匯鑽卡"], subcat_map["國內一般消費"], "cashback", 2.22, None, None, None, None),
        (card_map["匯鑽卡"], subcat_map["加油"], "cashback", 2.22, None, None, None, None),
    ]
    cursor.executemany(
        """INSERT OR IGNORE INTO rewards
           (card_id, category_id, reward_type, reward_rate, reward_cap, conditions, start_date, end_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        rewards,
    )

    # === 商家（示範，未來接 Google Places）===
    merchants = [
        ("星巴克", subcat_map["咖啡店"], None, None, None),
        ("路易莎", subcat_map["咖啡店"], None, None, None),
        ("7-ELEVEN", subcat_map["超商"], None, None, None),
        ("全家便利商店", subcat_map["超商"], None, None, None),
        ("麥當勞", subcat_map["速食"], None, None, None),
        ("Uber Eats", subcat_map["外送平台"], None, None, None),
        ("foodpanda", subcat_map["外送平台"], None, None, None),
        ("全聯", subcat_map["超市"], None, None, None),
        ("家樂福", subcat_map["量販店"], None, None, None),
        ("中油", subcat_map["加油"], None, None, None),
        ("台灣高鐵", subcat_map["大眾運輸"], None, None, None),
        ("Booking.com", subcat_map["訂房網站"], None, None, None),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO merchants (name, category_id, google_place_id, lat, lng) VALUES (?, ?, ?, ?, ?)",
        merchants,
    )

    conn.commit()
    conn.close()
    print("種子資料已匯入完成!")


if __name__ == "__main__":
    seed()
