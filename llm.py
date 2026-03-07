"""
CardBrain 3.0 LLM 意圖萃取
自然語言 → {mode, merchant, amount, destination, budget, breakdown}
LLM 只做 NLU（意圖解析），不做數學計算。
無 API key 時自動降級為規則式解析。
"""

import json
import os
import re

# ── 設定 ──────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "openai", or "anthropic"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

_SYSTEM_PROMPT = """你是 CardBrain 的意圖解析器。使用者會用中文自然語言描述消費或旅遊計畫。
請分析使用者輸入，回傳 JSON（不要包含其他文字）：

{
  "mode": "instant" | "regret" | "plan",
  "merchant": "商家名稱（若有）",
  "amount": 數字（若有）,
  "destination": "目的地（若為旅遊）",
  "budget": 數字（旅遊總預算）,
  "breakdown": {"flights": 數字, "hotels": 數字, "shopping": 數字, "dining": 數字, "transport": 數字}
}

規則：
- 提到商家+金額 → mode=instant
- 提到旅遊/出國/目的地 → mode=plan
- 只有商家沒有金額 → mode=instant, amount=null
- 預算若只有總額，按 30/25/25/10/10 比例拆分 breakdown
- 只回傳 JSON，不要其他文字"""


def extract_intent(user_input: str) -> dict:
    """
    解析自然語言意圖。有 LLM API key 時用 LLM，否則降級為規則式解析。
    """
    if LLM_API_KEY and LLM_PROVIDER:
        try:
            return _llm_extract(user_input)
        except Exception:
            pass
    return _rule_extract(user_input)


# ── LLM 解析（httpx） ────────────────────────────

def _llm_extract(user_input: str) -> dict:
    import httpx

    if LLM_PROVIDER == "gemini":
        model = LLM_MODEL or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={LLM_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_input}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 500,
                "responseMimeType": "application/json",
            },
        }
        resp = httpx.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_response(content)

    elif LLM_PROVIDER == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        model = LLM_MODEL or "gpt-4o-mini"
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            "temperature": 0,
            "max_tokens": 500,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_response(content)

    elif LLM_PROVIDER == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        model = LLM_MODEL or "claude-sonnet-4-5-20250929"
        headers = {
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_input}],
            "temperature": 0,
            "max_tokens": 500,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]
        return _parse_json_response(content)

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def _parse_json_response(text: str) -> dict:
    """從 LLM 回應中提取 JSON。"""
    # 嘗試直接解析
    text = text.strip()
    # 移除 markdown code fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ── 規則式解析（fallback） ──────────────────────────

# 旅遊關鍵字
_TRAVEL_KEYWORDS = ["旅遊", "出國", "旅行", "行程", "自由行", "跟團"]
_DESTINATIONS = ["日本", "韓國", "泰國", "歐洲", "美國", "東京", "大阪", "京都", "首爾", "曼谷", "沖繩", "北海道"]

# 金額 pattern：支援 "300", "300元", "2000塊", "10萬", "3.5萬"
_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*萬")
_AMOUNT_SIMPLE_RE = re.compile(r"(\d{2,})\s*(?:元|塊)?(?:\s|$|，|,|。)")


def _rule_extract(user_input: str) -> dict:
    """規則式意圖解析：regex 提取商家名 + 金額 + 旅遊關鍵字。"""
    text = user_input.strip()
    result = {"mode": "instant"}

    # 檢查是否為旅遊模式
    is_travel = any(kw in text for kw in _TRAVEL_KEYWORDS)
    destination = None
    for dest in _DESTINATIONS:
        if dest in text:
            destination = dest
            is_travel = True
            break

    # 提取金額
    amount = _extract_amount(text)

    if is_travel and destination:
        result["mode"] = "plan"
        result["destination"] = destination
        if amount:
            result["budget"] = amount
            result["breakdown"] = {
                "flights": round(amount * 0.30),
                "hotels": round(amount * 0.25),
                "shopping": round(amount * 0.25),
                "dining": round(amount * 0.10),
                "transport": round(amount * 0.10),
            }
        return result

    # 即時推薦模式：提取商家名
    # 移除金額部分，剩餘的可能是商家名
    merchant = _extract_merchant(text)
    if merchant:
        result["merchant"] = merchant
    if amount:
        result["amount"] = amount

    return result


def _extract_amount(text: str) -> float | None:
    """從文字中提取金額。"""
    # 先找 X萬
    m = _AMOUNT_RE.search(text)
    if m:
        return float(m.group(1)) * 10000

    # 再找普通數字
    m = _AMOUNT_SIMPLE_RE.search(text)
    if m:
        return float(m.group(1))

    # 最後找任意數字序列
    numbers = re.findall(r"\d+", text)
    if numbers:
        # 取最大的數字作為金額（啟發式）
        vals = [int(n) for n in numbers]
        biggest = max(vals)
        if biggest >= 10:  # 忽略太小的數字
            return float(biggest)

    return None


def _extract_merchant(text: str) -> str | None:
    """從文字中提取商家名稱（移除金額和常見詞後的剩餘部分）。"""
    cleaned = text
    # 移除金額相關
    cleaned = _AMOUNT_RE.sub("", cleaned)
    cleaned = _AMOUNT_SIMPLE_RE.sub("", cleaned)
    # 移除常見動詞和介詞
    for word in ["在", "去", "到", "花", "刷", "買", "吃", "喝", "消費", "結帳", "付"]:
        cleaned = cleaned.replace(word, " ")
    # 移除數字
    cleaned = re.sub(r"\d+", "", cleaned)
    # 清理空白
    cleaned = cleaned.strip()
    # 取第一個有意義的詞
    parts = [p.strip() for p in re.split(r"[\s，,。]+", cleaned) if p.strip()]
    return parts[0] if parts else None
