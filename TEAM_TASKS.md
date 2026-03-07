# CardBrain 卡比獸隊 — 工作分配

> **JetThAI Hackathon #1 | 目標：3/18 前完成初版 → 包裝成 Skill → 當天快速組裝**

## 團隊成員

| 成員 | 角色 | 負責領域 |
|------|------|----------|
| **Sunu** | 工程師 | 部署 + Zeabur + Skill 包裝 |
| **Stone** | 工程師 | 前端功能 + UX 優化 |
| **Alan** | 工程師 | 後端 API + 資料庫擴充 |
| **Rita** | 工程師 | PWA + 基礎建設 + 效能 |
| **Hera** | 美術 | UI 設計 + 視覺素材 + 簡報 |
| **Wade** | QA | 測試 + Bug 回報 + 驗收 |

---

## 工作分配

### Sunu — 工程師 / 部署 + Skill 包裝

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| S1 | Zeabur 部署管理 | Docker build → Zeabur 部署，確保線上環境穩定 | ⬜ |
| S2 | Skill 包裝策略 | 定義哪些模組要包成獨立 Skill，確保 3/18 能快速組裝 | ⬜ |
| S3 | 部署 Skill 包裝 | 整理 `zeabur-deploy-skill`，確保一鍵部署可用 | ⬜ |
| S4 | 環境變數整理 | 整理所有環境變數，建立 `.env.example` | ⬜ |
| S5 | CI/CD 自動化 | GitHub push → 自動部署到 Zeabur（如可行） | ⬜ |

### Stone — 前端工程師

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| F1 | 地圖體驗優化 | 地圖互動改善：標記點擊動畫、商家列表與地圖聯動、搜尋結果標記在地圖上 | ⬜ |
| F2 | 卡片比較功能 | 結果頁支援「選 2 張卡比較」回饋差異 | ⬜ |
| F3 | 推薦結果分享 | 推薦結果可產生分享連結或截圖 | ⬜ |
| F4 | 離線體驗優化 | Service Worker 離線時顯示已快取的卡片資料和上次推薦 | ⬜ |
| F5 | 前端 Skill 包裝 | 把 SPA 前端整理成可快速部署的 Skill（含 router、components） | ⬜ |

### Alan — 後端工程師

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| B1 | 擴充信用卡資料 | 從 Money101 補齊更多銀行/卡片/回饋規則（目前 19 銀行 43 卡，目標 25+ 銀行 60+ 卡） | ⬜ |
| B2 | 擴充商家對照表 | `merchant_aliases.py` 補更多 OSM 商家名稱對照（目前 46 商家） | ⬜ |
| B3 | Nearby API 優化 | 改善 Overpass API 查詢效率，增加 POI 類型覆蓋（如藥妝、書店） | ⬜ |
| B4 | API 錯誤處理強化 | 加入 rate limit 保護、Overpass fallback、錯誤回傳格式統一 | ⬜ |
| B5 | 資料庫 Skill 包裝 | 把 `database/` 模組整理成可獨立執行的 Skill（含 seed data） | ⬜ |

### Rita — 工程師 / PWA + 基礎建設

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| D1 | PWA 完善 | 確認 manifest.json icons、splash screen、安裝提示都正常 | ⬜ |
| D2 | 離線體驗優化 | Service Worker 離線時顯示已快取的卡片資料和上次推薦 | ⬜ |
| D3 | 效能監控 | 加入基本的 API response time logging | ⬜ |
| D4 | PWA Skill 包裝 | 把 PWA 配置整理成可快速套用的 Skill | ⬜ |

### Hera — 美術 / UI 設計

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| U1 | UI 風格定義 | 定義配色、字型、圓角等視覺規範（目前是紫色系 #6C5CE7） | ⬜ |
| U2 | 卡片視覺升級 | 「我的卡組合」卡片縮圖加上各銀行 Logo 或更精緻的設計 | ⬜ |
| U3 | 地圖標記設計 | 設計比 emoji 更精緻的商家標記圖示（分類 icon set） | ⬜ |
| U4 | App Icon + Splash | 設計 PWA icon（192x192, 512x512）和啟動畫面 | ⬜ |
| U5 | Hackathon 簡報 | 製作 Demo Day 簡報投影片（產品介紹 + 技術架構 + Demo） | ⬜ |
| U6 | OG Image | 設計社群分享時的 Open Graph 預覽圖 | ⬜ |

### Wade — QA 測試

| # | 任務 | 說明 | 狀態 |
|---|------|------|------|
| Q1 | 功能測試清單 | 建立完整功能測試 checklist（卡片管理、搜尋、分類、地圖、推薦） | ⬜ |
| Q2 | 跨裝置測試 | 測試 iPhone Safari / Android Chrome / 桌面 Chrome，記錄問題 | ⬜ |
| Q3 | 定位精度測試 | 不同環境（室內/室外/WiFi/行動網路）測試定位精度和商家匹配 | ⬜ |
| Q4 | Edge Case 測試 | 無網路、定位被拒、0 張卡、搜尋空結果等邊界情況 | ⬜ |
| Q5 | 效能測試 | API 回應時間、首次載入速度、地圖渲染流暢度 | ⬜ |
| Q6 | Bug 追蹤 | 統一在 GitHub Issues 回報 bug，標記優先級 | ⬜ |

---

## 優先級指引

### P0 — 必須完成（Demo 核心路徑）
- B1 擴充信用卡資料（Alan）
- B2 擴充商家對照表（Alan）
- F1 地圖體驗優化（Stone）
- S1 Zeabur 部署管理（Sunu）
- U4 App Icon（Hera）
- U5 簡報（Hera）
- Q1 功能測試清單（Wade）
- Q2 跨裝置測試（Wade）

### P1 — 應該完成（加分項）
- B3 Nearby API 優化（Alan）
- F2 卡片比較（Stone）
- D1 PWA 完善（Rita）
- U1 UI 風格定義（Hera）
- U2 卡片視覺升級（Hera）

### P2 — 有時間再做
- B4 API 錯誤處理（Alan）
- F3 推薦分享（Stone）
- D2 離線體驗（Rita）
- D3 效能監控（Rita）
- S5 CI/CD（Sunu）
- U3 地圖標記設計（Hera）
- U6 OG Image（Hera）

### Skill 包裝（3/18 前必須完成）
- S2 Skill 包裝策略（Sunu）
- S3 部署 Skill（Sunu）
- B5 資料庫 Skill（Alan）
- F5 前端 Skill（Stone）
- D4 PWA Skill（Rita）

---

## 現有技術架構

```
FastAPI 單一容器（API + 靜態前端）
部署於 Zeabur，Dockerfile 自動建置

後端: Python / FastAPI / SQLite
前端: 純 HTML / CSS / JS（無框架）、SPA hash router
地圖: Leaflet + OpenStreetMap（免費，無需 API key）
定位: Overpass API (OSM) + Geolocation API + Notification API
PWA: manifest.json + Service Worker (network-first)
部署: Docker → Zeabur
```

## 已知問題

| 問題 | 狀態 | 負責 |
|------|------|------|
| 桌面瀏覽器定位精度差（IP 定位偏移） | 已加精度圈提示 | Stone |
| Leaflet z-index 穿透 Modal | 已修復 | Stone |
| 商家對照表覆蓋不足 | 待擴充 | Alan |

---

*最後更新：2026-03-07*
