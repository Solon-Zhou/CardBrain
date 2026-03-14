# CardBrain - 隨身刷卡大腦

> **JetThAI Hackathon | 第一隊 #1 — 卡比獸**
>
> AI Agent 幫你秒算最佳刷卡推薦。走到商家附近自動推薦最佳刷卡！

## 產品概述

**CardBrain** 是一個 PWA + Capacitor 混合應用，透過 Gemini Function Calling Agent 聊天介面，使用者只要描述消費情境，就能自動取得最佳刷卡建議。

### 核心功能

| 功能 | 說明 |
|------|------|
| **AI 助理** | 輸入「星巴克 300」「日本 6000 日幣」，Gemini Agent 自動判斷意圖、精算回饋、用人話回覆 |
| **我的卡片** | 管理卡組合，每張卡可展開查看各分類回饋優惠（回饋率/類型/上限/條件） |
| **卡片比對** | 選 2 張卡片，比較各分類回饋差異 |
| **附近商家** | Leaflet 地圖偵測 500m 內商家，顯示最佳刷卡推薦 |
| **精算引擎** | 三種模式 — 即時推薦(instant)、後悔計算機(regret)、行程規劃(plan) |
| **外幣換算** | 自動辨識外幣金額、即時匯率換算、計算海外手續費與淨回饋 |

---

## 系統架構

```
FastAPI 單一容器（API + 靜態前端）
部署於 Zeabur，Dockerfile 自動建置
資料庫：Supabase PostgreSQL（線上）/ SQLite（本地 fallback）

card/
├── app.py                    # FastAPI 入口（SPA fallback）
├── brain.py                  # 精算引擎（instant / regret / plan）
├── llm.py                    # Gemini Function Calling Agent
├── exchange.py               # 外幣換算 + 匯率快取
├── requirements.txt
├── Dockerfile
│
├── routes/
│   ├── agent.py              # POST /api/agent + /api/brain
│   ├── cards.py              # GET /api/cards/* endpoints
│   └── nearby.py             # GET /api/nearby（地圖 + 推薦）
│
├── database/
│   ├── init_db.py            # SQLite schema（6 張表）
│   ├── seed_data.py          # 種子資料（22 銀行 / 52 卡 / 163 回饋 / 49 商家）
│   ├── query.py              # 查詢引擎（雙模式 SQLite / PostgreSQL）
│   ├── merchant_aliases.py   # OSM 商家名稱對照（100+ 別名）
│   └── cards.db              # SQLite（本地開發用）
│
├── templates/
│   └── index.html            # SPA shell（底部 Tab Bar）
│
├── static/
│   ├── manifest.json          # PWA
│   ├── sw.js                  # Service Worker（network-first）
│   ├── css/style.css          # Mobile-first CSS（~1200 行）
│   └── js/
│       ├── app.js             # SPA hash router
│       ├── api.js             # API 呼叫封裝（9 個函式）
│       ├── config.js          # 環境偵測（PWA / Capacitor）
│       ├── store.js           # localStorage 卡片管理
│       ├── geo.js             # Geolocation 封裝
│       ├── notify.js          # Notification API 封裝
│       ├── capacitor-bridge.js # 背景定位 + 本地通知橋接
│       └── pages/
│           ├── home.js        # AI 助理（Agent 聊天 UI）
│           ├── cards.js       # 我的卡片（可展開回饋明細）
│           ├── compare.js     # 卡片比對（選 2 張比較）
│           ├── nearby.js      # 附近商家（Leaflet 地圖）
│           └── result.js      # 查詢結果頁
│
├── android/                   # Capacitor Android 專案
├── capacitor.config.json      # Capacitor 配置
└── scripts/
    └── build-cap.sh           # www/ 組裝腳本
```

---

## 後端架構

### 核心資料流（Gemini Function Calling Agent）

```
使用者訊息 "星巴克 300"
    ↓
POST /api/agent { message, history, card_ids }
    ↓
llm.agent_chat()
    ↓
Gemini FC 決定呼叫 instant_recommend
    ↓
brain.instant_recommend("星巴克", 300, card_ids)
    ↓
Gemini 根據工具結果生成自然語言回覆
    ↓
回傳 { reply, history, tool_results }
```

**核心原則**：LLM 負責意圖理解 + 選擇工具 + 包裝回覆，精算引擎負責算錢 — LLM 不做數學。

### 精算引擎 (brain.py)

| 模式 | 輸入 | 輸出 |
|------|------|------|
| **instant** | 商家 + 金額 | 各卡回饋排名 + 實際回饋金額 |
| **regret** | 消費紀錄 | 你的回饋 vs 最佳回饋 vs 少賺多少 |
| **plan** | 目的地 + 預算 | 各類別最佳卡 + 帶卡清單 + 預估省下 |

### LLM 層 (llm.py) — Gemini Function Calling Agent

| 函式 | 功能 |
|------|------|
| `agent_chat()` | Agent 主迴圈：多輪對話 + 工具呼叫 + 自然語言回覆 |
| `_gemini_request()` | 封裝 Gemini REST API 呼叫 |
| `_execute_tool()` | 分派到 brain.py 三大工具 + 外幣換算 |
| `_trim_tool_result()` | 精簡結果減少 token 消耗 |

**3 個 Tool Declarations**：
1. `instant_recommend` — 單筆消費推薦（支援外幣 currency 欄位）
2. `plan_trip` — 旅遊行程規劃（支援外幣 budget_currency 欄位）
3. `regret_calculate` — 後悔計算機

### 外幣換算 (exchange.py)

| 功能 | 說明 |
|------|------|
| 匯率來源 | tw.rter.info API（USD 為基準交叉換算） |
| 快取機制 | DB 快取 TTL 1 小時，stale-on-error 容錯 |
| 中文幣別 | 支援「日幣」「美金」「韓元」等中文別名 → ISO 4217 |
| 手續費 | 海外消費預設 1.5% 手續費，與回饋分開計算 |

---

## 前端架構

### 頁面導覽（底部 Tab Bar）

```
index.html
  ├── 底部 Tab Bar
  │     ├── 🏠 首頁      → #/           (home.js)
  │     ├── ⚖️ 比對      → #/compare    (compare.js)
  │     ├── 📍 優惠      → #/nearby     (nearby.js)
  │     └── 💳 我的      → #/cards      (cards.js)
  │
  └── #/result → result.js  查詢結果頁
```

### 頁面生命週期

每個頁面遵循相同結構，含 destroy 清理機制：

```javascript
async function PageName(params) {
  const data = await API.getData();
  return `<div>...</div>`;
}

PageName.init = (params) => {
  // DOM ready 後綁定事件
};

PageName.destroy = () => {
  // 清理 listener、定時器、地圖等資源
};
```

### CSS 命名空間

| 前綴 | 用途 |
|------|------|
| `.agent-*` | AI 助理聊天 UI |
| `.cd-*` | 卡片管理（card detail） |
| `.nearby-*` | 附近商家地圖 |
| `.cmp-*` | 卡片比對（compare） |
| `.tab-*` | 底部 Tab Bar |
| `.modal-*` | Modal 對話框 |

---

## API Endpoints

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/cards` | 全部信用卡清單 |
| GET | `/api/cards/{id}/rewards` | 某張卡的全部回饋規則 |
| GET | `/api/categories` | 巢狀分類結構 |
| GET | `/api/recommend/merchant?q=星巴克&card_ids=1,5` | 商家推薦 |
| GET | `/api/recommend/category?category_id=23&card_ids=1,5` | 分類推薦 |
| GET | `/api/merchants/search?q=星` | 商家 autocomplete |
| POST | `/api/brain` | 精算引擎（instant/regret/plan） |
| POST | `/api/agent` | AI Agent（Gemini FC + 精算 + 回覆） |
| GET | `/api/nearby?lat=25.03&lng=121.56&card_ids=1,5` | 附近商家推薦 |

---

## 資料庫

### 雙模式架構

| 環境 | 模式 | 說明 |
|------|------|------|
| **線上 (Zeabur)** | PostgreSQL | 設定 `DATABASE_URL` → 連接 Supabase |
| **本地開發** | SQLite | 無 `DATABASE_URL` → 自動使用 `cards.db` |

### Schema（6 張表）

```
banks (22)  → cards (52)  → rewards (163)  → categories (42)
                                              merchants (49)
                                              exchange_rates (匯率快取)
```

| 表 | 欄位 | 說明 |
|----|------|------|
| `banks` | id, name, logo_url | 22 家銀行 |
| `cards` | id, bank_id, card_name, annual_fee, note | 52 張信用卡 |
| `categories` | id, parent_id, name, icon | 8 主分類 + 34 子分類（樹狀） |
| `rewards` | id, card_id, category_id, reward_type, reward_rate, reward_cap, conditions, start_date, end_date | 163 筆回饋規則 |
| `merchants` | id, name, category_id, lat, lng | 49 家常見商家 |
| `exchange_rates` | currency_code, rate_to_twd, updated_at | 匯率快取（TTL 1 小時） |

### 資料關係

```
商家 → 消費分類 → 回饋規則 → 信用卡 → 銀行
星巴克 → 咖啡店 → 3.3% points → CUBE 卡 → 國泰世華
```

---

## 快速開始

### 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 初始化資料庫 + 種子資料
python -m database.init_db
python -m database.seed_data

# 啟動開發伺服器
uvicorn app:app --reload
```

瀏覽器開啟 `http://localhost:8000`

### Docker

```bash
docker build -t cardbrain .
docker run -p 8000:8000 cardbrain
```

### Capacitor Android

```bash
bash scripts/build-cap.sh    # 組裝 www/
npx cap sync                 # 同步到 android/
npx cap build android        # 編譯 APK
```

### 環境變數

| 變數 | 必要 | 說明 |
|------|------|------|
| `LLM_API_KEY` | AI 功能必須 | Gemini API Key |
| `LLM_MODEL` | 選用 | 預設 `gemini-2.5-flash` |
| `DATABASE_URL` | 選用 | Supabase PostgreSQL 連接字串（無則用 SQLite） |
| `GOOGLE_PLACES_API_KEY` | 選用 | Google Places API（無則 fallback Overpass/OSM） |

---

## 技術棧

| 層 | 技術 |
|----|------|
| 後端 | Python / FastAPI |
| 資料庫 | Supabase PostgreSQL（線上）/ SQLite（本地） |
| 精算引擎 | brain.py（純 Python 計算） |
| LLM | Gemini 2.5 Flash（Function Calling Agent） |
| 外幣 | tw.rter.info API + DB 快取 |
| 前端 | 純 HTML / CSS / JS（無框架）、SPA hash router |
| 地圖 | Leaflet + OpenStreetMap |
| Geofencing | Google Places / Overpass API + Geolocation + Notification |
| PWA | manifest.json + Service Worker (network-first) |
| App | Capacitor v8（Android） |
| 部署 | Docker → Zeabur |

---

## 團隊

**卡比獸** — JetThAI Hackathon 第一隊 (隊號 #1)
