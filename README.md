# CardBrain - 隨身刷卡大腦

> **JetThAI Hackathon | 第一隊 #1 — 卡比獸**
>
> 選好你的卡，搜商家或選分類，秒看最佳刷卡推薦。

## 產品概述

**CardBrain** 是一個 PWA 前端應用，讓使用者選擇自己擁有的信用卡，搜尋商家或瀏覽分類取得最佳刷卡推薦。

### 核心功能

- **我的卡組合** — 搜尋銀行/卡名，一鍵新增/移除
- **商家搜尋** — 輸入商家名稱，即時 autocomplete，查看推薦卡片
- **分類瀏覽** — 8 大消費分類 + 34 子分類，點選查看回饋排行
- **智慧推薦** — 區分「我有的卡」vs「其他推薦」，有卡優先顯示
- **回饋計算機** — 輸入消費金額，即時算出每張卡的回饋金額（含月上限警示）
- **Fallback 機制** — 無回饋規則的商家自動回退到「國內一般消費」分類

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
        └── pages/
            ├── home.js        # 首頁：卡片管理 + 搜尋 + 分類（一頁式）
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
| PWA | manifest.json + Service Worker (network-first) |
| 部署 | Docker → Zeabur |

---

## 團隊

**卡比獸** — JetThAI Hackathon 第一隊 (隊號 #1)
