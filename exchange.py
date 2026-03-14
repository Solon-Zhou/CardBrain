"""
匯率查詢快取模組
- DB 快取 TTL 1 小時（stale-on-error 容錯）
- API 來源：https://tw.rter.info/capi.php（USD 為基準）
- 回傳包含換算明細的 dict，供 llm._execute_tool() 使用
"""

import logging
import sqlite3
from datetime import datetime, timezone

import httpx

from database.query import get_conn as _get_conn

# ── 常數 ──────────────────────────────────────────────────────────────────────
OVERSEAS_FEE_RATE = 0.015       # 海外手續費預設值（1.5%）
CACHE_TTL_SECONDS = 3600        # 匯率快取 1 小時
EXCHANGE_RATE_API = "https://tw.rter.info/capi.php"

# 中文幣別別名對照表（LLM 可能傳來中文）
CURRENCY_ALIASES: dict[str, str] = {
    "日幣": "JPY", "日圓": "JPY", "円": "JPY",
    "美金": "USD", "美元": "USD",
    "港幣": "HKD", "港元": "HKD",
    "歐元": "EUR",
    "英鎊": "GBP",
    "韓元": "KRW", "韓幣": "KRW",
    "澳幣": "AUD", "澳元": "AUD",
    "加幣": "CAD", "加元": "CAD",
    "新加坡幣": "SGD", "新幣": "SGD",
    "泰銖": "THB", "泰幣": "THB",
    "人民幣": "CNY", "人民币": "CNY",
    "新台幣": "TWD", "台幣": "TWD",
}


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _normalize_currency(code: str) -> str:
    """正規化幣別代碼：別名轉 ISO 4217 大寫。"""
    code = code.strip()
    # 先嘗試別名對照（支援中文）
    if code in CURRENCY_ALIASES:
        return CURRENCY_ALIASES[code]
    return code.upper()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_rate_from_api(currency_code: str) -> float:
    """
    從 tw.rter.info 取得匯率。
    公式：USDTWD.Exrate / USD{code}.Exrate = 1 {code} 兌台幣
    TWD 直接回傳 1.0。
    """
    if currency_code == "TWD":
        return 1.0

    resp = httpx.get(EXCHANGE_RATE_API, timeout=10)
    resp.raise_for_status()
    data: dict = resp.json()

    usd_twd_key = "USDTWD"
    usd_code_key = f"USD{currency_code}"

    if usd_twd_key not in data:
        raise RuntimeError("API 未回傳 USDTWD 匯率")
    if usd_code_key not in data:
        raise ValueError(f"不支援的幣別：{currency_code}（API 無 {usd_code_key}）")

    usd_twd = float(data[usd_twd_key]["Exrate"])
    usd_code = float(data[usd_code_key]["Exrate"])

    if usd_code == 0:
        raise RuntimeError(f"{usd_code_key} Exrate 為 0，資料異常")

    rate = usd_twd / usd_code
    return round(rate, 6)


def _upsert_rate(currency_code: str, rate: float) -> None:
    """將匯率寫入 DB（INSERT OR REPLACE）。"""
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO exchange_rates (currency_code, rate_to_twd, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(currency_code) DO UPDATE SET
                rate_to_twd = excluded.rate_to_twd,
                updated_at  = excluded.updated_at
            """,
            (currency_code, rate, _now_utc_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def _query_cached_rate(currency_code: str) -> tuple[float | None, bool]:
    """
    查詢 DB 快取。
    回傳 (rate, is_fresh)：
      - rate=None → 無快取
      - is_fresh=True → 在 TTL 內
      - is_fresh=False → 有快取但已過期（stale）
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT rate_to_twd, updated_at FROM exchange_rates WHERE currency_code = ?",
            (currency_code,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None, False

    rate = float(row["rate_to_twd"])
    updated_at_str = row["updated_at"]

    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_seconds = (now - updated_at).total_seconds()
        is_fresh = age_seconds <= CACHE_TTL_SECONDS
    except Exception:
        is_fresh = False

    return rate, is_fresh


# ── 公開 API ──────────────────────────────────────────────────────────────────

def get_rate(currency_code: str) -> float:
    """
    取得 1 單位外幣兌台幣的匯率。
    優先使用 DB 快取；過期時呼叫 API 並更新快取。
    API 失敗時：有過期快取 → stale-on-error；無快取 → raise RuntimeError。
    """
    code = _normalize_currency(currency_code)

    # 台幣直接回傳
    if code == "TWD":
        return 1.0

    # 查快取
    cached_rate, is_fresh = _query_cached_rate(code)
    if cached_rate is not None and is_fresh:
        logging.debug("匯率快取命中：%s = %.6f TWD", code, cached_rate)
        return cached_rate

    # 快取過期或無快取 → 打 API
    try:
        rate = _fetch_rate_from_api(code)
        _upsert_rate(code, rate)
        logging.info("匯率已更新：%s = %.6f TWD", code, rate)
        return rate
    except ValueError:
        # 不支援的幣別（API 無此代碼）
        raise
    except Exception as e:
        if cached_rate is not None:
            # stale-on-error：使用過期快取
            logging.warning(
                "匯率 API 失敗（%s），使用過期快取 %.6f TWD：%s", code, cached_rate, e
            )
            return cached_rate
        raise RuntimeError(f"無法取得 {code} 匯率，且無快取可用：{e}") from e


def convert_to_twd(
    amount: float,
    currency_code: str,
    card_overseas_fee_rate: float | None = None,
) -> dict:
    """
    將外幣金額換算為台幣，並計算海外手續費。

    回傳 dict：
      - base_twd   : 換算後台幣（不含手續費，傳給 brain.py 的金額）
      - fee_amount : 手續費台幣金額（單獨呈現，不加進回饋計算）
      - is_foreign : 是否為外幣（台幣時 False）
    """
    code = _normalize_currency(currency_code)

    if code == "TWD":
        return {
            "original_amount": amount,
            "currency_code": "TWD",
            "rate_to_twd": 1.0,
            "base_twd": amount,
            "fee_rate": 0.0,
            "fee_amount": 0.0,
            "display_text": "",
            "fee_text": "",
            "is_foreign": False,
        }

    rate = get_rate(code)
    base_twd = round(amount * rate, 2)

    fee_rate = card_overseas_fee_rate if card_overseas_fee_rate is not None else OVERSEAS_FEE_RATE
    fee_amount = round(base_twd * fee_rate, 2)

    display_text = f"{amount:g} {code} = {base_twd} TWD（匯率 {rate}）"
    fee_text = f"海外手續費 {fee_rate * 100:.1f}% = ${fee_amount}"

    return {
        "original_amount": amount,
        "currency_code": code,
        "rate_to_twd": rate,
        "base_twd": base_twd,
        "fee_rate": fee_rate,
        "fee_amount": fee_amount,
        "display_text": display_text,
        "fee_text": fee_text,
        "is_foreign": True,
    }
