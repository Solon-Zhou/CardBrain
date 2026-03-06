"""
信用卡優惠本地資料庫 - 初始化腳本
使用 SQLite，零依賴，資料庫檔案: cards.db
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cards.db")


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 銀行
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            logo_url TEXT
        )
    """)

    # 信用卡
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_id INTEGER NOT NULL,
            card_name TEXT NOT NULL,
            image_url TEXT,
            annual_fee INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (bank_id) REFERENCES banks(id)
        )
    """)

    # 消費分類（樹狀結構，參考 iCard.AI 的 8 大類 / 60+ 子分類）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL,
            icon TEXT,
            FOREIGN KEY (parent_id) REFERENCES categories(id)
        )
    """)

    # 回饋規則（核心：哪張卡在哪個分類有多少回饋）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL CHECK(reward_type IN ('cashback', 'points', 'miles')),
            reward_rate REAL NOT NULL,
            reward_cap REAL,
            conditions TEXT,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (card_id) REFERENCES cards(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # 商家（未來對接 Google Places，做 Geofencing 用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            google_place_id TEXT,
            lat REAL,
            lng REAL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"資料庫已建立: {DB_PATH}")


if __name__ == "__main__":
    init_database()
