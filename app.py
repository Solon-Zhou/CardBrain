"""
CardBrain PWA — FastAPI 後端
同時 serve API + 靜態前端
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# 載入 .env（本地開發用；Zeabur 由 dashboard 設定）
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(title="CardBrain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://localhost",
        "http://localhost",
        "capacitor://localhost",
        "ionic://localhost",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 掛載 routes ────────────────────────────────────────
from routes.agent import router as agent_router
from routes.cards import router as cards_router
from routes.nearby import router as nearby_router

app.include_router(agent_router)
app.include_router(cards_router)
app.include_router(nearby_router)

# ── 靜態檔 + SPA fallback ────────────────────────────
BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

_index_html = (BASE / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str = ""):
    return _index_html
