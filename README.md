# CardBrain - 隨身刷卡大腦

> **JetThAI Hackathon | 第一隊 #1 — 卡比獸**
>
> AI Agent 幫你秒算最佳刷卡推薦。走到商家附近自動推薦最佳刷卡！

## 產品概述

**CardBrain** 是一個 PWA 應用，透過 AI Agent 聊天介面，使用者只要描述消費情境，就能自動取得最佳刷卡建議。

### 核心功能

| 功能 | 說明 |
|------|------|
| **AI 助理** | 輸入「星巴克 300」「日本旅遊 10萬」，Agent 自動判斷意圖、精算回饋、用人話回覆 |
| **我的卡片** | 管理卡組合，每張卡可展開查看各分類回饋優惠（回饋率/類型/上限/條件） |
| **附近商家** | Leaflet 地圖偵測 500m 內商家，顯示最佳刷卡推薦 |
| **精算引擎** | 三種模式 — 即時推薦(instant)、後悔計算機(regret)、行程規劃(plan) |
| **智慧回退** | 無 LLM API key 時自動 fallback 模板式回覆 |

---

## 系統架構

```
FastAPI 單一容器（API + 靜態前端）
部署於 Zeabur，Dockerfile 自動建置

card/
├── app.py                    # FastAPI 入口（9 個 API + SPA fallback）
├── brain.py                  # 精算引擎（instant / regret / plan）
├── llm.py                    # LLM 層（意圖解析 + 自然語言回覆）
├── requirements.txt
├── Dockerfile
│
├── database/
│   ├── init_db.py            # SQLite schema（5 張表）
│   ├── seed_data.py          # 種子資料
│   ├── query.py              # 查詢引擎（8 個查詢函式）
│   ├── merchant_aliases.py   # OSM 商家名稱對照
│   └── cards.db              # SQLite（Docker build 時重建）
│
├── templates/
│   └── index.html            # SPA shell（漢堡選單 + 側邊導覽）
│
└── static/
    ├── manifest.json          # PWA
    ├── sw.js                  # Service Worker v32（network-first）
    ├── css/style.css          # Mobile-first CSS（~1200 行）
    └── js/
        ├── app.js             # SPA hash router + 漢堡選單邏輯
        ├── api.js             # API 呼叫封裝（9 個函式）
        ├── store.js           # localStorage 卡片管理
        ├── geo.js             # Geolocation 封裝
        ├── notify.js          # Notification API 封裝
        └── pages/
            ├── home.js        # AI 助理（Agent 聊天 UI）
            ├── cards.js       # 我的卡片（可展開回饋明細）
            ├── nearby.js      # 附近商家（Leaflet 地圖）
            └── result.js      # 查詢結果頁
```

---

## 後端架構

### 核心資料流

```
使用者訊息 "星巴克 300"
    ↓
POST /api/agent
    ↓
llm.extract_intent()      →  { mode: "instant", merchant: "星巴克", amount: 300 }
    ↓
brain.instant_recommend()  →  { results: [{ card, rate, reward }...] }
    ↓
llm.generate_reply()       →  "刷國泰 CUBE 卡可獲得 9.9 小樹點..."
    ↓
回傳 { reply, mode, data }
```

**核心原則**：LLM 負責聽懂 + 包裝人話，精算引擎負責算錢 — LLM 不做數學。

### 精算引擎 (brain.py)

| 模式 | 輸入 | 輸出 |
|------|------|------|
| **instant** | 商家 + 金額 | 各卡回饋排名 + 實際回饋金額 |
| **regret** | 消費紀錄 | 你的回饋 vs 最佳回饋 vs 少賺多少 |
| **plan** | 目的地 + 預算 | 各類別最佳卡 + 帶卡清單 + 預估省下 |

### LLM 層 (llm.py)

| 函式 | 功能 |
|------|------|
| `extract_intent()` | NLU 意圖解析（Gemini/OpenAI/Anthropic，含 regex fallback） |
| `generate_reply()` | 把精算結果包裝成自然語言回覆 |
| `_template_reply()` | 無 API key 時的模板式 fallback |

---

## 前端架構

### 頁面導覽

```
index.html
  ├── 漢堡選單 ☰ → 側邊導覽 (sidenav)
  │     ├── 💬 AI 助理    → #/
  │     ├── 💳 我的卡片   → #/cards
  │     └── 📍 附近商家   → #/nearby
  │
  ├── #/         → home.js     AI Agent 聊天介面
  ├── #/cards    → cards.js    卡片管理 + 可展開回饋明細
  ├── #/nearby   → nearby.js   Leaflet 互動地圖
  └── #/result   → result.js   商家/分類推薦結果
```

### 頁面開發模式

每個頁面遵循相同結構：

```javascript
async function PageName(params) {
  const data = await API.getData();  // 非同步取得資料
  return `<div>...</div>`;           // 回傳 HTML 字串
}

PageName.init = (params) => {
  // DOM ready 後綁定事件
};
```

### CSS 命名空間

| 前綴 | 用途 |
|------|------|
| `.agent-*` | Agent 聊天 UI |
| `.cd-*` | 卡片管理（card detail） |
| `.nearby-*` | 附近商家地圖 |
| `.sidenav-*` | 漢堡選單 / 側邊導覽 |
| `.modal-*` | 新增卡片 Modal |

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
| POST | `/api/agent` | AI Agent（NLU + 精算 + 回覆） |
| GET | `/api/nearby?lat=25.03&lng=121.56&card_ids=1,5` | 附近商家推薦 |

---

## 資料庫

### Schema

```
banks (19)      → cards (43)     → rewards (170+)    → categories (42)
                                                        merchants (46)
```

| 表 | 欄位 | 說明 |
|----|------|------|
| `banks` | id, name, logo_url | 19 家銀行 |
| `cards` | id, bank_id, card_name, annual_fee, note | 43 張信用卡 |
| `categories` | id, parent_id, name, icon | 8 主分類 + 34 子分類（樹狀） |
| `rewards` | id, card_id, category_id, reward_type, reward_rate, reward_cap, conditions | 170+ 筆回饋規則 |
| `merchants` | id, name, category_id, lat, lng | 46 家常見商家 |

### 資料關係

```
商家 → 消費分類 → 回饋規則 → 信用卡 → 銀行
星巴克 → 咖啡店 → 3.3% points → CUBE 卡 → 國泰世華
```

---

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 初始化資料庫 + 種子資料
python -m database.init_db
python -m database.seed_data

# 啟動開發伺服器
uvicorn app:app --reload

# 測試 Agent
curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"message":"星巴克 300","card_ids":[1,5]}'
```

瀏覽器開啟 `http://localhost:8000`

### Docker

```bash
docker build -t cardbrain .
docker run -p 8000:8000 cardbrain
```

### 環境變數（選用）

```
LLM_PROVIDER=gemini        # gemini / openai / anthropic
LLM_API_KEY=your-key-here  # 無 key 則自動 fallback 模板回覆
```

---

## 技術棧

| 層 | 技術 |
|----|------|
| 後端 | Python / FastAPI / SQLite |
| 精算引擎 | brain.py（純 Python 計算） |
| LLM | Gemini / OpenAI / Anthropic（可切換，含 fallback） |
| 前端 | 純 HTML / CSS / JS（無框架）、SPA hash router |
| 地圖 | Leaflet + OpenStreetMap |
| Geofencing | Overpass API + Geolocation API + Notification API |
| PWA | manifest.json + Service Worker (network-first) |
| 部署 | Docker → Zeabur |

---

## 團隊

**卡比獸** — JetThAI Hackathon 第一隊 (隊號 #1)
