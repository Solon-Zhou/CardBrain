# CardBrain - 隨身刷卡大腦

> **JetThAI Hackathon | 第一隊 #1 — 卡比獸**
>
> 走進店家的瞬間，手機自動告訴你該刷哪張卡。

## 產品願景

目前市面上的信用卡優惠服務（如 iCard.AI、Money101），仍需要使用者**手動輸入店家**查詢，體驗不夠直覺。

**CardBrain** 要打造的是真正全自動的「隨身刷卡大腦」：

- 事前設定你擁有的信用卡（個人化卡包）
- 走進星巴克 → 手機自動推播：『建議刷國泰 CUBE 卡，回饋 3%』
- **結帳零思考**

### 核心技術

| 技術 | 用途 |
|------|------|
| **LBS 地理圍欄 (Geofencing)** | 自動偵測使用者進入商家範圍 |
| **Google Places API** | 辨識附近商家名稱 |
| **匹配引擎** | 商家 → 消費分類 → 最佳卡片 |
| **推播通知** | 即時推送刷卡建議 |

---

## 系統架構

```
使用者手機
  │
  ├── 地理圍欄偵測 (Geofencing)
  │     └── 進入商家範圍時觸發
  │
  ├── 個人化卡包 (My Cards)
  │     └── 使用者設定擁有的信用卡
  │
  └── 推播通知 (Push Notification)
        └── 自動推送最佳刷卡建議
              │
              ▼
         Backend API
              │
  ┌───────────┼───────────┐
  ▼           ▼           ▼
位置比對    優惠匹配    通知引擎
Location   Offer Match  Push Service
Matching   Engine
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  商家 DB   信用卡    Google
  + 位置   優惠 DB   Places API
```

---

## 資料庫結構

```
banks          → 銀行（國泰、中信、玉山...）
cards          → 信用卡（CUBE卡、LINE Pay卡...）
categories     → 消費分類（8大類 / 60+ 子分類）
rewards        → 回饋規則（哪張卡在哪個分類有多少 % 回饋）
merchants      → 商家（名稱、分類、GPS 座標）
```

### 資料關係

```
商家 → 消費分類 → 回饋規則 → 信用卡 → 銀行
星巴克 → 咖啡店 → 3% cashback → CUBE 卡 → 國泰世華
```

---

## 開發階段

### Phase 1: 資料基礎 (目前)
- [x] 本地 SQLite 資料庫架構
- [x] 種子資料（8 張熱門卡、17 個子分類、12 家商家）
- [x] 查詢引擎 MVP（商家 → 最佳卡片）
- [ ] 爬蟲：從 Money101 擴充信用卡資料
- [ ] 爬蟲：從銀行官網補充回饋規則
- [ ] 完善消費分類 ↔ 商家對應

### Phase 2: 後端 API
- [ ] RESTful API（查詢最佳卡片）
- [ ] 使用者卡包管理（CRUD）
- [ ] 部署到雲端（Supabase / 其他）

### Phase 3: 前端 + Geofencing
- [ ] PWA 前端介面
- [ ] Web Geolocation API 整合
- [ ] Google Places API 商家辨識
- [ ] Web Push Notification 推播

### Phase 4: 進階功能
- [ ] 原生 APP（iOS/Android）
- [ ] 背景定位 + 地理圍欄
- [ ] 即時優惠更新機制
- [ ] 社群分享功能

---

## 專案結構

```
card/
├── README.md              # 本文件
├── database/
│   ├── init_db.py         # 資料庫初始化
│   ├── seed_data.py       # 種子資料
│   ├── query.py           # 查詢引擎
│   └── cards.db           # SQLite 資料庫檔案
├── scraper/               # (待建) 資料爬蟲
└── api/                   # (待建) 後端 API
```

---

## 快速開始

```bash
# 1. 初始化資料庫
python database/init_db.py

# 2. 匯入種子資料
python database/seed_data.py

# 3. 執行 Demo
python database/query.py
```

---

## 參考資料來源

| 來源 | 用途 |
|------|------|
| [Money101](https://www.money101.com.tw/) | 信用卡產品資料 |
| [iCard.AI](https://icard.ai/diagnosis) | 消費分類體系參考 |
| 各銀行官網 | 回饋規則細節 |
| Google Places API | 商家位置辨識 |

---

## 團隊

**卡比獸** — JetThAI Hackathon 第一隊 (隊號 #1)
