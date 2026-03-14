"""
種子資料 - 2026 年台灣主流信用卡完整資料
資料來源：Money101、各銀行官網公開資訊
最後更新：2026/03
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cards.db")


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ============================================================
    # 銀行（22 家）
    # ============================================================
    banks = [
        ("國泰世華",),
        ("中國信託",),
        ("玉山銀行",),
        ("台新銀行",),
        ("永豐銀行",),
        ("富邦銀行",),
        ("聯邦銀行",),
        ("滙豐銀行",),
        ("遠東商銀",),
        ("第一銀行",),
        ("美國運通",),
        ("星展銀行",),
        ("凱基銀行",),
        ("新光銀行",),
        ("華南銀行",),
        ("兆豐銀行",),
        ("渣打銀行",),
        ("合作金庫",),
        ("台灣企銀",),
        ("元大銀行",),
        ("上海商銀",),
        ("彰化銀行",),
    ]
    cursor.executemany("INSERT OR IGNORE INTO banks (name) VALUES (?)", banks)

    # ============================================================
    # 消費分類（8 大類 + 子分類）
    # ============================================================
    main_categories = [
        (None, "常用消費", "shopping-cart"),
        (None, "繳費與保險", "receipt"),
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

    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    cat_map = {name: cid for cid, name in cursor.fetchall()}

    sub_categories = [
        # 常用消費
        (cat_map["常用消費"], "國內一般消費", None),
        (cat_map["常用消費"], "海外消費", None),
        (cat_map["常用消費"], "網購", None),
        (cat_map["常用消費"], "行動支付", None),
        (cat_map["常用消費"], "超商", None),
        (cat_map["常用消費"], "超市", None),
        (cat_map["常用消費"], "量販店", None),
        # 繳費與保險
        (cat_map["繳費與保險"], "保費", None),
        (cat_map["繳費與保險"], "繳稅", None),
        (cat_map["繳費與保險"], "水電瓦斯", None),
        (cat_map["繳費與保險"], "電信費", None),
        # 百貨購物
        (cat_map["百貨購物"], "百貨公司", None),
        (cat_map["百貨購物"], "藥妝", None),
        (cat_map["百貨購物"], "寵物用品", None),
        # 餐飲外送
        (cat_map["餐飲外送"], "咖啡店", None),
        (cat_map["餐飲外送"], "速食", None),
        (cat_map["餐飲外送"], "外送平台", None),
        (cat_map["餐飲外送"], "餐廳", None),
        (cat_map["餐飲外送"], "早餐店", None),
        # 通勤交通
        (cat_map["通勤交通"], "加油", None),
        (cat_map["通勤交通"], "停車", None),
        (cat_map["通勤交通"], "大眾運輸", None),
        (cat_map["通勤交通"], "ETC", None),
        (cat_map["通勤交通"], "高鐵", None),
        # 娛樂休閒
        (cat_map["娛樂休閒"], "影音串流", None),
        (cat_map["娛樂休閒"], "遊戲", None),
        (cat_map["娛樂休閒"], "電影院", None),
        # 其他
        (cat_map["其他"], "綠色消費", None),
        (cat_map["其他"], "電動車充電", None),
        # 旅遊住宿
        (cat_map["旅遊住宿"], "訂房網站", None),
        (cat_map["旅遊住宿"], "航空公司", None),
        (cat_map["旅遊住宿"], "旅行社", None),
        (cat_map["旅遊住宿"], "日本消費", None),
        (cat_map["旅遊住宿"], "韓國消費", None),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO categories (parent_id, name, icon) VALUES (?, ?, ?)",
        sub_categories,
    )

    # ============================================================
    # 信用卡（40 張）
    # ============================================================
    cursor.execute("SELECT id, name FROM banks")
    bank_map = {name: bid for bid, name in cursor.fetchall()}

    cards = [
        # 國泰世華
        (bank_map["國泰世華"], "CUBE 卡", 0,
         "最高3.3%小樹點無上限，四大權益可切換，慶生月最高10%"),
        # 中國信託
        (bank_map["中國信託"], "LINE Pay 卡", 1800,
         "綁LINE Pay免年費，訂房最高16%，海外2.8%（含國外加碼至2026/6/30）"),
        (bank_map["中國信託"], "foodpanda 聯名卡", 1800,
         "外送最高30%回饋幣，餐廳15%"),
        (bank_map["中國信託"], "uniopen 聯名卡", 0,
         "海外實體店最高11%，免登錄無最低消費"),
        # 玉山銀行
        (bank_map["玉山銀行"], "U Bear 卡", 0,
         "行動支付/網購/國外最高10%，影音平台最高10%，需帳戶扣繳"),
        (bank_map["玉山銀行"], "Unicard", 3000,
         "百大通路最高4.5%，新戶最高7.5%"),
        (bank_map["玉山銀行"], "Pi 拍錢包信用卡", 0,
         "Pi錢包加碼最高3-4% P幣，全家優惠"),
        (bank_map["玉山銀行"], "熊本熊卡", 0,
         "日本一般消費2.5%無上限，指定日本商店最高8.5%"),
        # 台新銀行
        (bank_map["台新銀行"], "Richart 卡", 1500,
         "七大方案60通路最高3.8%，LINE Pay 2.3%，首年免年費"),
        (bank_map["台新銀行"], "FlyGo 卡", 0,
         "海外消費最高5%，旅遊訂房首選"),
        # 永豐銀行
        (bank_map["永豐銀行"], "DAWHO 現金回饋卡", 0,
         "大戶等級國內3.5%/國外4.5%，大戶Plus國內5%/國外6%"),
        (bank_map["永豐銀行"], "幣倍卡", 3000,
         "海外最高10%（新戶），雙幣卡，4次/年機場貴賓室"),
        (bank_map["永豐銀行"], "DAWAY 卡", 3000,
         "LINE Pay最高6%（新戶），首年免年費"),
        (bank_map["永豐銀行"], "現金回饋 Green 卡", 0,
         "國內1%/國外2%現金回饋無上限"),
        (bank_map["永豐銀行"], "保倍卡", 3000,
         "保費1.2%回饋，首年免年費"),
        (bank_map["永豐銀行"], "現金回饋 JCB 卡", 0,
         "特選通路含網購5%，綁全支付加碼3%，國外最高10%"),
        # 富邦銀行
        (bank_map["富邦銀行"], "J 卡", 0,
         "日韓3%無上限+實體加碼3%+交通卡加碼7%，最高13%"),
        # 聯邦銀行
        (bank_map["聯邦銀行"], "賴點卡", 0,
         "LINE Points 回饋"),
        (bank_map["聯邦銀行"], "LINE Bank 聯名卡", 0,
         "影音/網購/遊戲4%月上限300元（至2026/7/31），含momo/蝦皮/Netflix"),
        # 滙豐銀行
        (bank_map["滙豐銀行"], "匯鑽卡", 2000,
         "行動支付/網購/外送/國外最高6%，上限2000元/月，需設自動扣繳，一般1%無上限"),
        (bank_map["滙豐銀行"], "Live+ 現金回饋卡", 2000,
         "購物通路3.88%上限888元/月，國內最高4.88%，海外5.88%"),
        (bank_map["滙豐銀行"], "現金回饋御璽卡", 2000,
         "國內1.22%/國外2.22%無上限無門檻，保費分期3.88%"),
        # 遠東商銀
        (bank_map["遠東商銀"], "快樂信用卡", 2000,
         "國內線上5%，悠遊加值5%，百貨5%"),
        (bank_map["遠東商銀"], "樂家+ 卡", 2000,
         "寵物商店10%，外送2.5%，海外2.5%無上限"),
        (bank_map["遠東商銀"], "樂行卡", 2000,
         "交通/旅遊3%，國外2%"),
        (bank_map["遠東商銀"], "C'est Moi 卡", 2000,
         "百貨9折，高鐵3%，海外3% HAPPY GO"),
        # 第一銀行
        (bank_map["第一銀行"], "iLEO 卡", 1200,
         "海外最高13%（新戶），行動支付3%，首年免年費"),
        (bank_map["第一銀行"], "一卡通聯名卡", 300,
         "早餐店5%，日韓3.5%，國內2%"),
        (bank_map["第一銀行"], "icash 聯名卡", 1200,
         "7-ELEVEN 10%，國外5%"),
        (bank_map["第一銀行"], "御璽商旅卡", 2000,
         "旅遊15%，行動支付5%，國外3%"),
        # 美國運通
        (bank_map["美國運通"], "長榮航空白金卡", 36800,
         "國內25元/哩，國外16.67元/哩，新戶首刷65000哩"),
        # 星展銀行
        (bank_map["星展銀行"], "eco 永續卡", 0,
         "國內1.0%無上限，國外最高5%（至2026/12/31），綠色消費最高10%"),
        (bank_map["星展銀行"], "傳說對決聯名卡", 0,
         "國內1.2%無上限，國外2.5%無上限，生活玩家精選通路10%"),
        # 凱基銀行
        (bank_map["凱基銀行"], "魔BUY卡", 0,
         "綁Apple Pay享4%，行動支付14大支付，需月消費滿3000"),
        # 新光銀行
        (bank_map["新光銀行"], "寰宇現金回饋卡", 0,
         "海外3%，指定數位3%，國內1%，需完成任務"),
        # 華南銀行
        (bank_map["華南銀行"], "超鑽現金回饋卡", 0,
         "國內最高2%，國外最高3.2%，需完成三項任務，加碼上限2000元"),
        (bank_map["華南銀行"], "i網購生活卡", 0,
         "網購最高2%回饋"),
        # 兆豐銀行
        (bank_map["兆豐銀行"], "利多御璽卡", 0,
         "綁行動支付最高6%，台灣Pay掃碼加碼1.5%，合計最高7.5%"),
        (bank_map["兆豐銀行"], "e秒刷鈦金卡", 0,
         "一般0.5%，網購3%上限月刷10000，需電子帳單+自動扣繳"),
        # 渣打銀行
        (bank_map["渣打銀行"], "渣打現金回饋御璽卡", 0,
         "國內外1%，加油/高鐵/航空1.5%（至2026/6/30），優先理財最高2%"),
        # 合作金庫
        (bank_map["合作金庫"], "卡娜赫拉綠卡", 0,
         "國內1%/國外2%無上限，行動支付台灣Pay最高11%，上限低"),
        (bank_map["合作金庫"], "i享樂生活卡", 0,
         "國內1%/國外2%無上限，悠遊加值5%/LINE Pay 6%上限各100元/月"),
        # 台灣企銀
        (bank_map["台灣企銀"], "永續生活卡", 0,
         "國內最高2.5%，國外最高3.5%，綠色餐廳10%，高鐵8.5%"),
        # 美國運通
        (bank_map["美國運通"], "金卡", 0,
         "外幣/電信/外送/旅行社2%（免任務），無特殊條件限制"),
        # 凱基銀行
        (bank_map["凱基銀行"], "誠品悠遊御璽卡", 0,
         "一般消費2%（月上限400點），誠品消費另有加碼"),
        # 新光銀行
        (bank_map["新光銀行"], "SKM 聯名卡", 0,
         "新光三越假日0.9%，生日月3%，停車優惠"),
        # 兆豐銀行
        (bank_map["兆豐銀行"], "悠遊聯名卡", 0,
         "台灣Pay 2%，悠遊付10%（上限$300），月上限$1,000"),
        # 合作金庫
        (bank_map["合作金庫"], "無限金鑽卡", 0,
         "國內外1%無上限，保費加碼0.5%（單筆NT$200,000+）"),
        # 元大銀行
        (bank_map["元大銀行"], "鑽金卡", 0,
         "國內1.2%/海外2.2%無門檻無上限"),
        # 聯邦銀行
        (bank_map["聯邦銀行"], "吉鶴卡", 0,
         "旅日2.5%無上限，任務疊加最高11%"),
        # 上海商銀
        (bank_map["上海商銀"], "小小兵回饋卡", 0,
         "國內1.234%/國外2.234%，指定通路最高5%"),
        # 彰化銀行
        (bank_map["彰化銀行"], "My 樂現金回饋卡", 0,
         "國內0.5%/國外1%無上限，台灣Pay加碼3.5%"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO cards (bank_id, card_name, annual_fee, note) VALUES (?, ?, ?, ?)",
        cards,
    )

    # ============================================================
    # 回饋規則
    # ============================================================
    cursor.execute("SELECT id, card_name FROM cards")
    card_map = {name: cid for cid, name in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NOT NULL")
    subcat_map = {name: cid for cid, name in cursor.fetchall()}

    rewards = [
        # --- 國泰 CUBE 卡 ---
        (card_map["CUBE 卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),
        (card_map["CUBE 卡"], subcat_map["網購"], "points", 3.3, None, "玩數位方案"),
        (card_map["CUBE 卡"], subcat_map["咖啡店"], "points", 3.3, None, "樂饗購方案"),
        (card_map["CUBE 卡"], subcat_map["外送平台"], "points", 3.3, None, "樂饗購方案"),
        (card_map["CUBE 卡"], subcat_map["餐廳"], "points", 3.3, None, "樂饗購方案"),
        (card_map["CUBE 卡"], subcat_map["訂房網站"], "points", 3.3, None, "趣旅行方案"),
        (card_map["CUBE 卡"], subcat_map["航空公司"], "points", 3.3, None, "趣旅行方案"),

        # --- 中信 LINE Pay 卡 ---
        (card_map["LINE Pay 卡"], subcat_map["國內一般消費"], "points", 1.0, None, "LINE Points"),
        (card_map["LINE Pay 卡"], subcat_map["海外消費"], "points", 2.8, None, "國內1%+國外加碼1.8%（至2026/6/30），LINE Points"),
        (card_map["LINE Pay 卡"], subcat_map["行動支付"], "points", 3.0, None, "LINE Pay 綁定"),
        (card_map["LINE Pay 卡"], subcat_map["訂房網站"], "points", 16.0, None, "指定訂房平台"),

        # --- 中信 foodpanda 卡 ---
        (card_map["foodpanda 聯名卡"], subcat_map["外送平台"], "points", 30.0, None, "foodpanda 回饋幣"),
        (card_map["foodpanda 聯名卡"], subcat_map["餐廳"], "points", 15.0, None, "回饋幣"),
        (card_map["foodpanda 聯名卡"], subcat_map["國內一般消費"], "points", 1.0, None, None),

        # --- 中信 uniopen ---
        (card_map["uniopen 聯名卡"], subcat_map["海外消費"], "cashback", 11.0, 500, "海外實體店，免登錄"),
        (card_map["uniopen 聯名卡"], subcat_map["國內一般消費"], "cashback", 3.0, None, "需於中信App完成uniopen會員帳號連結，踩點任務至2026/6/30"),

        # --- 玉山 U Bear ---
        (card_map["U Bear 卡"], subcat_map["網購"], "cashback", 10.0, None, "國內外線上消費，需帳戶扣繳"),
        (card_map["U Bear 卡"], subcat_map["行動支付"], "cashback", 10.0, None, "需帳戶扣繳"),
        (card_map["U Bear 卡"], subcat_map["影音串流"], "cashback", 10.0, None, "Netflix/Disney+"),
        (card_map["U Bear 卡"], subcat_map["海外消費"], "cashback", 10.0, None, "需帳戶扣繳"),
        (card_map["U Bear 卡"], subcat_map["超商"], "cashback", 3.0, None, None),
        (card_map["U Bear 卡"], subcat_map["外送平台"], "cashback", 3.0, None, None),
        (card_map["U Bear 卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),

        # --- 玉山 Unicard ---
        (card_map["Unicard"], subcat_map["網購"], "points", 4.5, None, "百大通路 UP選"),
        (card_map["Unicard"], subcat_map["行動支付"], "points", 4.5, None, "百大通路"),
        (card_map["Unicard"], subcat_map["百貨公司"], "points", 4.5, None, "百大通路"),

        # --- 玉山 Pi 拍錢包 ---
        (card_map["Pi 拍錢包信用卡"], subcat_map["超商"], "cashback", 4.0, None, "全家/Pi錢包"),
        (card_map["Pi 拍錢包信用卡"], subcat_map["網購"], "cashback", 3.0, None, "Pi錢包"),
        (card_map["Pi 拍錢包信用卡"], subcat_map["保費"], "cashback", 1.2, None, None),

        # --- 玉山 熊本熊卡 ---
        (card_map["熊本熊卡"], subcat_map["日本消費"], "cashback", 2.5, None, "日本一般消費無上限"),
        (card_map["熊本熊卡"], subcat_map["海外消費"], "cashback", 2.5, None, None),

        # --- 台新 Richart ---
        (card_map["Richart 卡"], subcat_map["行動支付"], "points", 3.8, None, "指定方案60通路"),
        (card_map["Richart 卡"], subcat_map["網購"], "points", 3.8, None, "指定方案"),
        (card_map["Richart 卡"], subcat_map["海外消費"], "points", 3.3, None, None),
        (card_map["Richart 卡"], subcat_map["國內一般消費"], "points", 0.3, None, None),

        # --- 台新 FlyGo ---
        (card_map["FlyGo 卡"], subcat_map["海外消費"], "cashback", 5.0, None, None),
        (card_map["FlyGo 卡"], subcat_map["訂房網站"], "cashback", 5.0, None, None),
        (card_map["FlyGo 卡"], subcat_map["航空公司"], "cashback", 5.0, None, None),
        (card_map["FlyGo 卡"], subcat_map["旅行社"], "cashback", 5.0, None, None),

        # --- 永豐 DAWHO ---
        (card_map["DAWHO 現金回饋卡"], subcat_map["國內一般消費"], "cashback", 3.5, 400, "大戶等級，加碼上限400/月"),
        (card_map["DAWHO 現金回饋卡"], subcat_map["海外消費"], "cashback", 4.5, 400, "大戶等級"),

        # --- 永豐 幣倍卡 ---
        (card_map["幣倍卡"], subcat_map["海外消費"], "cashback", 4.0, None, "完成指定任務，新戶最高10%"),
        (card_map["幣倍卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),

        # --- 永豐 DAWAY ---
        (card_map["DAWAY 卡"], subcat_map["行動支付"], "points", 6.0, None, "LINE Pay新戶，LINE Points"),
        (card_map["DAWAY 卡"], subcat_map["國內一般消費"], "points", 0.5, None, "LINE Points"),
        (card_map["DAWAY 卡"], subcat_map["海外消費"], "points", 2.5, None, "LINE Points"),

        # --- 永豐 Green 卡 ---
        (card_map["現金回饋 Green 卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限"),
        (card_map["現金回饋 Green 卡"], subcat_map["海外消費"], "cashback", 2.0, None, "無上限"),
        (card_map["現金回饋 Green 卡"], subcat_map["綠色消費"], "cashback", 5.0, None, "綠色通路任務加碼，限期至2026/6/30"),

        # --- 永豐 保倍卡 ---
        (card_map["保倍卡"], subcat_map["保費"], "cashback", 1.2, None, "保費回饋"),

        # --- 永豐 JCB ---
        (card_map["現金回饋 JCB 卡"], subcat_map["網購"], "cashback", 5.0, None, "特選通路"),
        (card_map["現金回饋 JCB 卡"], subcat_map["海外消費"], "cashback", 10.0, None, "新戶加碼"),
        (card_map["現金回饋 JCB 卡"], subcat_map["行動支付"], "cashback", 3.0, None, "綁全支付"),

        # --- 富邦 J 卡 ---
        (card_map["J 卡"], subcat_map["日本消費"], "points", 6.0, None, "基本3%+加碼3%（至2026/3/31），需單筆滿1000，上限1000元/季"),
        (card_map["J 卡"], subcat_map["韓國消費"], "points", 6.0, None, "基本3%+加碼3%（至2026/3/31），需單筆滿1000，上限1000元/季"),
        (card_map["J 卡"], subcat_map["海外消費"], "points", 3.0, None, "無上限"),
        (card_map["J 卡"], subcat_map["大眾運輸"], "points", 13.0, None, "日韓交通卡加碼7%，需登錄限量，至2026/3/31"),

        # --- 聯邦 LINE Bank ---
        (card_map["LINE Bank 聯名卡"], subcat_map["影音串流"], "points", 4.0, 300, "Netflix/Disney+，LINE Points，至2026/7/31"),
        (card_map["LINE Bank 聯名卡"], subcat_map["網購"], "points", 4.0, 300, "momo/蝦皮/PChome，至2026/7/31"),
        (card_map["LINE Bank 聯名卡"], subcat_map["遊戲"], "points", 4.0, 300, "至2026/7/31"),

        # --- 滙豐 匯鑽卡 ---
        (card_map["匯鑽卡"], subcat_map["行動支付"], "cashback", 6.0, 2000, "需設自動扣繳，上限2000元/月"),
        (card_map["匯鑽卡"], subcat_map["網購"], "cashback", 6.0, 2000, "需設自動扣繳，國內外網購"),
        (card_map["匯鑽卡"], subcat_map["外送平台"], "cashback", 6.0, 2000, "需設自動扣繳"),
        (card_map["匯鑽卡"], subcat_map["影音串流"], "cashback", 6.0, 2000, "需設自動扣繳"),
        (card_map["匯鑽卡"], subcat_map["海外消費"], "cashback", 6.0, 2000, "需設自動扣繳"),
        (card_map["匯鑽卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限"),

        # --- 滙豐 Live+ ---
        (card_map["Live+ 現金回饋卡"], subcat_map["餐廳"], "cashback", 3.88, 888, "餐飲通路，自動扣繳任務可+1%至2026/6/30"),
        (card_map["Live+ 現金回饋卡"], subcat_map["網購"], "cashback", 3.88, 888, "購物通路"),
        (card_map["Live+ 現金回饋卡"], subcat_map["百貨公司"], "cashback", 3.88, 888, "購物通路"),
        (card_map["Live+ 現金回饋卡"], subcat_map["海外消費"], "cashback", 5.88, None, None),
        (card_map["Live+ 現金回饋卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),

        # --- 滙豐 御璽卡 ---
        (card_map["現金回饋御璽卡"], subcat_map["國內一般消費"], "cashback", 1.22, None, "無上限無門檻"),
        (card_map["現金回饋御璽卡"], subcat_map["海外消費"], "cashback", 2.22, None, "無上限"),
        (card_map["現金回饋御璽卡"], subcat_map["保費"], "cashback", 3.88, None, "保費分期"),

        # --- 遠東 快樂信用卡 ---
        (card_map["快樂信用卡"], subcat_map["網購"], "cashback", 5.0, None, "國內線上"),
        (card_map["快樂信用卡"], subcat_map["百貨公司"], "cashback", 5.0, None, None),
        (card_map["快樂信用卡"], subcat_map["大眾運輸"], "cashback", 5.0, None, "悠遊加值"),

        # --- 遠東 樂家+ ---
        (card_map["樂家+ 卡"], subcat_map["寵物用品"], "cashback", 10.0, None, "寵物商店"),
        (card_map["樂家+ 卡"], subcat_map["外送平台"], "cashback", 2.5, None, None),
        (card_map["樂家+ 卡"], subcat_map["海外消費"], "cashback", 2.5, None, "無上限"),

        # --- 遠東 樂行卡 ---
        (card_map["樂行卡"], subcat_map["大眾運輸"], "cashback", 3.0, None, "交通"),
        (card_map["樂行卡"], subcat_map["加油"], "cashback", 3.0, None, None),
        (card_map["樂行卡"], subcat_map["海外消費"], "cashback", 2.0, None, None),

        # --- 遠東 C'est Moi ---
        (card_map["C'est Moi 卡"], subcat_map["百貨公司"], "points", 10.0, None, "百貨9折，HAPPY GO"),
        (card_map["C'est Moi 卡"], subcat_map["高鐵"], "points", 3.0, None, "HAPPY GO"),
        (card_map["C'est Moi 卡"], subcat_map["海外消費"], "points", 3.0, None, "HAPPY GO"),

        # --- 第一銀行 iLEO ---
        (card_map["iLEO 卡"], subcat_map["行動支付"], "cashback", 3.0, None, "LINE Pay/街口，月消費達1000元觸發+1%加碼"),
        (card_map["iLEO 卡"], subcat_map["國內一般消費"], "cashback", 2.0, None, None),
        (card_map["iLEO 卡"], subcat_map["海外消費"], "cashback", 13.0, 2600, "新戶加碼10%，期間限定"),

        # --- 第一銀行 一卡通 ---
        (card_map["一卡通聯名卡"], subcat_map["早餐店"], "cashback", 5.0, None, None),
        (card_map["一卡通聯名卡"], subcat_map["日本消費"], "cashback", 3.5, None, None),
        (card_map["一卡通聯名卡"], subcat_map["韓國消費"], "cashback", 3.5, None, None),
        (card_map["一卡通聯名卡"], subcat_map["國內一般消費"], "cashback", 2.0, None, None),

        # --- 第一銀行 icash ---
        (card_map["icash 聯名卡"], subcat_map["超商"], "cashback", 10.0, None, "7-ELEVEN"),
        (card_map["icash 聯名卡"], subcat_map["海外消費"], "cashback", 5.0, None, None),

        # --- 第一銀行 御璽商旅 ---
        (card_map["御璽商旅卡"], subcat_map["訂房網站"], "cashback", 15.0, None, "旅遊通路"),
        (card_map["御璽商旅卡"], subcat_map["行動支付"], "cashback", 5.0, None, None),
        (card_map["御璽商旅卡"], subcat_map["海外消費"], "cashback", 3.0, None, None),

        # --- 美國運通 長榮白金 ---
        (card_map["長榮航空白金卡"], subcat_map["航空公司"], "miles", 6.0, None, "國外16.67元/哩"),
        (card_map["長榮航空白金卡"], subcat_map["國內一般消費"], "miles", 4.0, None, "國內25元/哩"),

        # --- 星展 eco 永續卡 ---
        (card_map["eco 永續卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限，2026年從1.2%降至1.0%"),
        (card_map["eco 永續卡"], subcat_map["海外消費"], "cashback", 5.0, None, "日韓泰歐美新加坡，含加碼3.8%，限期至2026/12/31"),
        (card_map["eco 永續卡"], subcat_map["日本消費"], "cashback", 5.0, None, "含加碼3.8%，限期至2026/12/31"),
        (card_map["eco 永續卡"], subcat_map["綠色消費"], "cashback", 10.0, None, "Tesla/Gogoro/社會企業"),
        (card_map["eco 永續卡"], subcat_map["電動車充電"], "cashback", 10.0, None, "Tesla充電/Gogoro電池"),

        # --- 星展 傳說對決聯名卡 ---
        (card_map["傳說對決聯名卡"], subcat_map["國內一般消費"], "cashback", 1.2, None, "無上限"),
        (card_map["傳說對決聯名卡"], subcat_map["海外消費"], "cashback", 2.5, None, "無上限"),
        (card_map["傳說對決聯名卡"], subcat_map["遊戲"], "cashback", 10.0, 3333, "生活玩家精選通路，上限3333元/月"),
        (card_map["傳說對決聯名卡"], subcat_map["影音串流"], "cashback", 10.0, 3333, "生活玩家精選通路"),

        # --- 凱基 魔BUY卡 ---
        (card_map["魔BUY卡"], subcat_map["行動支付"], "cashback", 4.0, None, "綁Apple Pay，月消費需滿3000"),
        (card_map["魔BUY卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),

        # --- 新光 寰宇現金回饋卡 ---
        (card_map["寰宇現金回饋卡"], subcat_map["海外消費"], "cashback", 3.0, None, "需完成任務"),
        (card_map["寰宇現金回饋卡"], subcat_map["網購"], "cashback", 3.0, None, "指定數位通路"),
        (card_map["寰宇現金回饋卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, None),
        (card_map["寰宇現金回饋卡"], subcat_map["行動支付"], "cashback", 3.0, 300, "台灣Pay，上限300元/月"),

        # --- 華南 超鑽現金回饋卡 ---
        (card_map["超鑽現金回饋卡"], subcat_map["國內一般消費"], "cashback", 2.0, 2000, "需完成三項任務，加碼上限2000元"),
        (card_map["超鑽現金回饋卡"], subcat_map["海外消費"], "cashback", 3.2, 2000, "需完成三項任務"),

        # --- 華南 i網購生活卡 ---
        (card_map["i網購生活卡"], subcat_map["網購"], "cashback", 2.0, None, None),

        # --- 兆豐 利多御璽卡 ---
        (card_map["利多御璽卡"], subcat_map["行動支付"], "cashback", 7.5, None, "綁行動支付6%+台灣Pay掃碼1.5%，需登錄"),
        (card_map["利多御璽卡"], subcat_map["國內一般消費"], "cashback", 0.5, None, None),

        # --- 兆豐 e秒刷鈦金卡 ---
        (card_map["e秒刷鈦金卡"], subcat_map["網購"], "cashback", 3.0, None, "月刷上限10000，需電子帳單+自動扣繳"),
        (card_map["e秒刷鈦金卡"], subcat_map["國內一般消費"], "cashback", 0.5, None, None),

        # --- 渣打 現金回饋御璽卡 ---
        (card_map["渣打現金回饋御璽卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "優先理財最高2%"),
        (card_map["渣打現金回饋御璽卡"], subcat_map["海外消費"], "cashback", 1.0, None, "優先理財最高2%"),
        (card_map["渣打現金回饋御璽卡"], subcat_map["加油"], "cashback", 1.5, None, "期間限定至2026/6/30"),
        (card_map["渣打現金回饋御璽卡"], subcat_map["高鐵"], "cashback", 1.5, None, "期間限定至2026/6/30"),
        (card_map["渣打現金回饋御璽卡"], subcat_map["航空公司"], "cashback", 1.5, None, "期間限定至2026/6/30"),

        # --- 合庫 卡娜赫拉綠卡 ---
        (card_map["卡娜赫拉綠卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限"),
        (card_map["卡娜赫拉綠卡"], subcat_map["海外消費"], "cashback", 2.0, None, "無上限"),
        (card_map["卡娜赫拉綠卡"], subcat_map["行動支付"], "cashback", 11.0, 1000, "台灣Pay，月消費滿2999，月刷上限1000，至2026/6/30"),

        # --- 合庫 i享樂生活卡 ---
        (card_map["i享樂生活卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限"),
        (card_map["i享樂生活卡"], subcat_map["海外消費"], "cashback", 2.0, None, "無上限"),
        (card_map["i享樂生活卡"], subcat_map["大眾運輸"], "cashback", 5.0, 100, "悠遊卡加值，月消費滿2999，上限100元/月"),

        # --- 台灣企銀 永續生活卡 ---
        (card_map["永續生活卡"], subcat_map["國內一般消費"], "cashback", 2.5, None, "需開Hokii帳戶扣繳，月帳單消費滿6000元，需登錄"),
        (card_map["永續生活卡"], subcat_map["海外消費"], "cashback", 3.5, None, None),
        (card_map["永續生活卡"], subcat_map["綠色消費"], "cashback", 10.0, None, "週五～日綠色餐廳，月消費滿6000元，加碼至2026/6/30"),
        (card_map["永續生活卡"], subcat_map["高鐵"], "cashback", 8.5, 300, "月消費滿20000，上限300元/月，加碼至2026/6/30"),

        # --- 台新 Richart 卡（補充保費） ---
        (card_map["Richart 卡"], subcat_map["保費"], "points", 1.3, None, "免切換免登錄，不含躉繳"),

        # --- 美國運通 金卡 ---
        (card_map["金卡"], subcat_map["海外消費"], "cashback", 2.0, None, "免任務"),
        (card_map["金卡"], subcat_map["電信費"], "cashback", 2.0, None, "免任務"),
        (card_map["金卡"], subcat_map["外送平台"], "cashback", 2.0, None, "免任務"),
        (card_map["金卡"], subcat_map["旅行社"], "cashback", 2.0, None, "免任務"),

        # --- 凱基 誠品悠遊御璽卡 ---
        (card_map["誠品悠遊御璽卡"], subcat_map["國內一般消費"], "points", 2.0, 400, "月上限400點"),
        (card_map["誠品悠遊御璽卡"], subcat_map["百貨公司"], "points", 2.0, 400, "誠品消費另有加碼"),

        # --- 新光 SKM 聯名卡 ---
        (card_map["SKM 聯名卡"], subcat_map["百貨公司"], "points", 0.9, None, "假日3倍點數，新光三越"),
        (card_map["SKM 聯名卡"], subcat_map["國內一般消費"], "points", 0.3, None, "月消費達NT$3,000"),

        # --- 兆豐 悠遊聯名卡 ---
        (card_map["悠遊聯名卡"], subcat_map["行動支付"], "cashback", 2.0, 1000, "台灣Pay QR Code掃碼，需登錄"),
        (card_map["悠遊聯名卡"], subcat_map["國內一般消費"], "cashback", 0.5, None, None),

        # --- 合庫 無限金鑽卡 ---
        (card_map["無限金鑽卡"], subcat_map["國內一般消費"], "cashback", 1.0, None, "無上限"),
        (card_map["無限金鑽卡"], subcat_map["海外消費"], "cashback", 2.0, None, "無上限"),
        (card_map["無限金鑽卡"], subcat_map["保費"], "cashback", 1.5, 10000, "含基礎1%+加碼0.5%，單筆NT$200,000+，至2026/12/31"),

        # --- 元大 鑽金卡 ---
        (card_map["鑽金卡"], subcat_map["國內一般消費"], "cashback", 1.2, None, "無門檻無上限，至2026/12/30"),
        (card_map["鑽金卡"], subcat_map["海外消費"], "cashback", 2.2, None, "無門檻無上限，至2026/12/30"),
        (card_map["鑽金卡"], subcat_map["行動支付"], "cashback", 3.2, None, "台灣Pay感應疊加+2%（至2026/12/31）"),

        # --- 聯邦 吉鶴卡 ---
        (card_map["吉鶴卡"], subcat_map["日本消費"], "cashback", 2.5, None, "無上限"),
        (card_map["吉鶴卡"], subcat_map["海外消費"], "cashback", 2.5, None, "Apple Pay+1.5%，任務疊加最高11%"),

        # --- 上海 小小兵回饋卡 ---
        (card_map["小小兵回饋卡"], subcat_map["國內一般消費"], "cashback", 1.234, None, None),
        (card_map["小小兵回饋卡"], subcat_map["海外消費"], "cashback", 2.234, None, None),
        (card_map["小小兵回饋卡"], subcat_map["超市"], "cashback", 5.0, 1000, "全聯需綁全支付，指定通路"),
        (card_map["小小兵回饋卡"], subcat_map["超商"], "cashback", 5.0, 1000, "指定通路"),

        # --- 彰銀 My 樂現金回饋卡 ---
        (card_map["My 樂現金回饋卡"], subcat_map["國內一般消費"], "cashback", 0.5, None, "無上限"),
        (card_map["My 樂現金回饋卡"], subcat_map["海外消費"], "cashback", 1.0, None, "無上限"),
        (card_map["My 樂現金回饋卡"], subcat_map["行動支付"], "cashback", 3.5, 200, "台灣Pay需每月1日登錄，月上限200元"),
    ]
    cursor.executemany(
        """INSERT OR IGNORE INTO rewards
           (card_id, category_id, reward_type, reward_rate, reward_cap, conditions)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rewards,
    )

    # ============================================================
    # 商家（40+ 家常見商家）
    # ============================================================
    merchants = [
        # 咖啡店
        ("星巴克", subcat_map["咖啡店"]),
        ("路易莎", subcat_map["咖啡店"]),
        ("cama cafe", subcat_map["咖啡店"]),
        # 超商
        ("7-ELEVEN", subcat_map["超商"]),
        ("全家便利商店", subcat_map["超商"]),
        ("萊爾富", subcat_map["超商"]),
        ("OK超商", subcat_map["超商"]),
        # 超市
        ("全聯", subcat_map["超市"]),
        ("美廉社", subcat_map["超市"]),
        # 量販店
        ("家樂福", subcat_map["量販店"]),
        ("好市多 Costco", subcat_map["量販店"]),
        ("大潤發", subcat_map["量販店"]),
        # 速食
        ("麥當勞", subcat_map["速食"]),
        ("肯德基", subcat_map["速食"]),
        ("摩斯漢堡", subcat_map["速食"]),
        ("漢堡王", subcat_map["速食"]),
        # 外送平台
        ("Uber Eats", subcat_map["外送平台"]),
        ("foodpanda", subcat_map["外送平台"]),
        # 餐廳
        ("王品集團", subcat_map["餐廳"]),
        ("鼎泰豐", subcat_map["餐廳"]),
        ("瓦城", subcat_map["餐廳"]),
        ("築間", subcat_map["餐廳"]),
        # 早餐店
        ("麥味登", subcat_map["早餐店"]),
        ("拉亞漢堡", subcat_map["早餐店"]),
        # 百貨公司
        ("新光三越", subcat_map["百貨公司"]),
        ("SOGO", subcat_map["百貨公司"]),
        ("微風廣場", subcat_map["百貨公司"]),
        ("遠東百貨", subcat_map["百貨公司"]),
        # 加油
        ("中油", subcat_map["加油"]),
        ("台塑", subcat_map["加油"]),
        # 大眾運輸
        ("台北捷運", subcat_map["大眾運輸"]),
        ("台灣高鐵", subcat_map["高鐵"]),
        ("台鐵", subcat_map["大眾運輸"]),
        # 網購
        ("momo購物網", subcat_map["網購"]),
        ("蝦皮購物", subcat_map["網購"]),
        ("PChome", subcat_map["網購"]),
        ("博客來", subcat_map["網購"]),
        # 影音串流
        ("Netflix", subcat_map["影音串流"]),
        ("Disney+", subcat_map["影音串流"]),
        ("Spotify", subcat_map["影音串流"]),
        # 訂房
        ("Booking.com", subcat_map["訂房網站"]),
        ("Agoda", subcat_map["訂房網站"]),
        ("Hotels.com", subcat_map["訂房網站"]),
        # 藥妝
        ("屈臣氏", subcat_map["藥妝"]),
        ("康是美", subcat_map["藥妝"]),
        # 寵物
        ("寵物公園", subcat_map["寵物用品"]),
        # 百貨（補充）
        ("誠品書店", subcat_map["百貨公司"]),
        # 綠色消費
        ("Gogoro", subcat_map["電動車充電"]),
        ("Tesla", subcat_map["電動車充電"]),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO merchants (name, category_id) VALUES (?, ?)",
        merchants,
    )

    conn.commit()

    # 統計
    counts = {}
    for table in ["banks", "cards", "categories", "rewards", "merchants"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    conn.close()

    print("種子資料匯入完成!")
    print(f"  銀行: {counts['banks']} 家")
    print(f"  信用卡: {counts['cards']} 張")
    print(f"  分類: {counts['categories']} 個")
    print(f"  回饋規則: {counts['rewards']} 筆")
    print(f"  商家: {counts['merchants']} 家")


if __name__ == "__main__":
    seed()
