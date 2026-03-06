# CardBrain - 隨身刷卡大腦

> **JetThAI Hackathon | 第一隊 #1 — 卡比獸**
>
> 選好你的卡，搜商家或選分類，秒看最佳刷卡推薦。走到商家附近自動推薦最佳刷卡！

## 產品概述

**CardBrain** 是一個 PWA 前端應用，讓使用者選擇自己擁有的信用卡，搜尋商家或瀏覽分類取得最佳刷卡推薦。

### 核心功能

- **我的卡組合** — 搜尋銀行/卡名，一鍵新增/移除
- **商家搜尋** — 輸入商家名稱，即時 autocomplete，查看推薦卡片
- **分類瀏覽** — 8 大消費分類 + 34 子分類，點選查看回饋排行
- **智慧推薦** — 區分「我有的卡」vs「其他推薦」，有卡優先顯示
- **回饋計算機** — 輸入消費金額，即時算出每張卡的回饋金額（含月上限警示）
- **Fallback 機制** — 無回饋規則的商家自動回退到「國內一般消費」分類
- **Geofencing 互動地圖** — Leaflet + OpenStreetMap 互動地圖，偵測附近 500m 商家以 emoji 標記顯示，點擊 popup 查看最佳刷卡推薦，推播通知

---

## 系統架構

```
FastAPI 單一容器（API + 靜態前端）
部署於 Zeabur，Dockerfile 自動建置

card/
├── app.py                    # FastAPI 入口（API + SPA fallback）
├── requirements.txt          # fastapi, uvicorn
├── Dockerfile                # Zeabur 部署用
├── database/
│   ├── __init__.py
│   ├── init_db.py            # SQLite schema
│   ├── seed_data.py          # 種子資料（19 銀行 / 43 卡 / 133 回饋規則 / 46 商家）
│   ├── query.py              # 查詢引擎（商家推薦、分類推薦、搜尋）
│   ├── merchant_aliases.py   # OSM 商家名稱對照表（Geofencing 用）
│   └── cards.db              # SQLite（.gitignore，Docker build 時重建）
├── templates/
│   └── index.html            # SPA shell
└── static/
    ├── manifest.json          # PWA
    ├── sw.js                  # Service Worker（network-first）
    ├── css/style.css          # Mobile-first CSS, max-width 480px
    └── js/
        ├── app.js             # SPA hash router
        ├── api.js             # API 呼叫封裝
        ├── store.js           # localStorage 卡片管理
        ├── geo.js             # 瀏覽器 Geolocation 封裝（Geofencing）
        ├── notify.js          # Notification API 封裝
        └── pages/
            ├── home.js        # 首頁：卡片管理 + 搜尋 + 分類 + 附近商家
            └── result.js      # 結果頁：推薦排序列表
```

---

## API Endpoints

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/cards` | 全部 43 張信用卡 |
| GET | `/api/categories` | 巢狀分類結構 |
| GET | `/api/recommend/merchant?q=星巴克&card_ids=1,5` | 商家推薦 |
| GET | `/api/recommend/category?category_id=23&card_ids=1,5` | 分類推薦 |
| GET | `/api/merchants/search?q=星` | 商家 autocomplete |
| GET | `/api/nearby?lat=25.03&lng=121.56&card_ids=1,5` | Geofencing 附近商家推薦 |
| GET | `/*` | SPA fallback (index.html) |

---

## 資料庫

```
banks (19)  → cards (43)  → rewards (133)  → categories (42)
                                              merchants (46)
```

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
```

瀏覽器開啟 `http://localhost:8000`

### Docker

```bash
docker build -t cardbrain .
docker run -p 8000:8000 cardbrain
```

---

## 技術棧

| 層 | 技術 |
|----|------|
| 後端 | Python / FastAPI / SQLite |
| 前端 | 純 HTML / CSS / JS（無框架）、SPA hash router |
| Geofencing | Overpass API (OSM) + Geolocation API + Notification API + Leaflet 互動地圖 |
| PWA | manifest.json + Service Worker (network-first) |
| 部署 | Docker → Zeabur |

---

## Geofencing 附近商家

### 運作流程

```
瀏覽器 Geolocation API
  → 取得 lat/lng（節流：60 秒間隔 + 50m 最小位移）
  → GET /api/nearby?lat=25.03&lng=121.56
      → 後端呼叫 Overpass API（查附近 500m POI）
      → merchant_aliases 對照表匹配 DB 商家
      → recommend_by_merchant() 取得最佳卡片
      → 回傳附近商家 + 推薦卡片（含 lat/lng 座標）
  → Leaflet 互動地圖：使用者藍色圓點 + 商家 emoji 標記
  → 點擊標記彈出 popup（商家名 + 最佳卡 + 回饋率 + 連結）
  → Notification API 推播通知
```

### API 回傳範例

```json
{
  "user_lat": 25.033,
  "user_lng": 121.565,
  "nearby": [
    {
      "merchant_name": "星巴克",
      "category_name": "咖啡店",
      "distance_m": 120,
      "lat": 25.034,
      "lng": 121.566,
      "top_card": {
        "bank_name": "國泰世華",
        "card_name": "CUBE 卡",
        "reward_rate": 3.3,
        "reward_type": "points",
        "conditions": "樂饗購方案"
      }
    }
  ]
}
```

### 注意事項

- **HTTPS 必要**：Geolocation API 需要 HTTPS（Zeabur 自帶 SSL）
- **通知權限被拒**：不影響首頁的附近商家 UI，通知只是加分
- **Overpass API 失敗**：靜默降級，不顯示附近區塊，不影響其他功能
- **Debug 模式**：API 支援 `debug_lat` / `debug_lng` 參數模擬位置

---

## 團隊

**卡比獸** — JetThAI Hackathon 第一隊 (隊號 #1)
