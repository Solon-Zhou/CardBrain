"""
CardBrain 3.0 LLM 意圖萃取
自然語言 → {mode, merchant, amount, destination, budget, breakdown}
LLM 只做 NLU（意圖解析），不做數學計算。
無 API key 時自動降級為規則式解析。
"""

import json
import logging
import os
import re

# ── 設定 ──────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "openai", or "anthropic"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
_LLM_TIMEOUT = 15  # 所有 LLM provider 統一超時秒數

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


_REPLY_SYSTEM_PROMPT = """你是 CardBrain 智慧刷卡助手。根據提供的精算結果 JSON，用親切的繁體中文回覆使用者。

規則：
- 直接講結論，不要囉唆
- 金額用 $ 符號，保留小數點後一位
- 若有最佳卡片，先說最佳卡 + 回饋金額
- 若有多張卡比較，簡要列出前 2-3 張
- 若是旅遊規劃，列出帶卡清單 + 總省錢金額
- 若是後悔計算，強調少賺金額，語氣帶點惋惜但鼓勵
- 不要用 markdown 格式，用純文字 + emoji
- 回覆控制在 200 字以內"""


def generate_reply(mode: str, intent: dict, brain_result: dict) -> str:
    """
    將 brain 精算結果包裝成自然語言回覆。
    有 API key 時呼叫 LLM，否則用模板式 fallback。
    """
    if LLM_API_KEY and LLM_PROVIDER:
        try:
            return _llm_reply(mode, intent, brain_result)
        except Exception as e:
            logging.warning("LLM reply fallback to template: %s", e)
    return _template_reply(mode, intent, brain_result)


def _llm_reply(mode: str, intent: dict, brain_result: dict) -> str:
    import httpx

    user_msg = json.dumps({"mode": mode, "intent": intent, "result": brain_result}, ensure_ascii=False)

    if LLM_PROVIDER == "gemini":
        model = LLM_MODEL or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={LLM_API_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": _REPLY_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400},
        }
        resp = httpx.post(url, json=payload, timeout=_LLM_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    elif LLM_PROVIDER == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        model = LLM_MODEL or "gpt-4o-mini"
        headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _REPLY_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=_LLM_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    elif LLM_PROVIDER == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        model = LLM_MODEL or "claude-sonnet-4-5-20250929"
        headers = {"x-api-key": LLM_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "system": _REPLY_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
            "temperature": 0.7,
            "max_tokens": 400,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=_LLM_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def _template_reply(mode: str, intent: dict, brain_result: dict) -> str:
    """模板式 fallback — 無 API key 時使用。"""
    if "error" in brain_result:
        return f"抱歉，我無法處理這個查詢：{brain_result['error']}"

    if mode == "instant":
        results = brain_result.get("results", [])
        if not results:
            return "找不到符合的信用卡推薦，試試其他商家或金額？"
        best = results[0]
        merchant = brain_result.get("merchant", "該商家")
        amount = brain_result.get("amount", 0)
        reply = f"在{merchant}消費 ${amount:,.0f}，推薦使用 {best['bank_name']} {best['card_name']}"
        reward = best.get("actual_reward", 0)
        rate = best.get("reward_rate", 0)
        rtype = best.get("reward_type", "cashback")
        unit = "回饋" if rtype == "cashback" else ("哩程" if rtype == "miles" else "點")
        reply += f"\n可獲得 ${reward:,.1f} {unit}（{rate}%）"
        if len(results) > 1:
            r2 = results[1]
            reply += f"\n第二推薦：{r2['bank_name']} {r2['card_name']}（${r2.get('actual_reward', 0):,.1f}）"
        return reply

    elif mode == "regret":
        total_regret = brain_result.get("total_regret", 0)
        total_your = brain_result.get("total_your_reward", 0)
        total_best = brain_result.get("total_best_reward", 0)
        if total_regret <= 0:
            return f"你的刷卡策略很棒！總回饋 ${total_your:,.1f}，已經是最佳選擇了"
        reply = f"你實際獲得 ${total_your:,.1f} 回饋，但最佳策略可得 ${total_best:,.1f}"
        reply += f"\n少賺了 ${total_regret:,.1f}！"
        details = brain_result.get("details", [])
        worst = max(details, key=lambda d: d.get("regret", 0), default=None)
        if worst and worst.get("regret", 0) > 0:
            reply += f"\n最大差距在「{worst['merchant']}」，建議改用 {worst['best_card']}"
        return reply

    elif mode == "plan":
        dest = brain_result.get("destination", "")
        total_savings = brain_result.get("total_savings", 0)
        cards_to_bring = brain_result.get("cards_to_bring", [])
        reply = f"去{dest}旅遊，預估可省下 ${total_savings:,.1f}！"
        if cards_to_bring:
            reply += "\n建議帶上："
            for c in cards_to_bring[:3]:
                usage = "、".join(c.get("usage", []))
                reply += f"\n- {c['card']}（{usage}）"
        return reply

    return "已收到你的查詢，但我不確定該如何回覆。請試試輸入商家+金額，或旅遊目的地+預算。"


def extract_intent(user_input: str) -> dict:
    """
    解析自然語言意圖。有 LLM API key 時用 LLM，否則降級為規則式解析。
    """
    if LLM_API_KEY and LLM_PROVIDER:
        try:
            return _llm_extract(user_input)
        except Exception as e:
            logging.warning("LLM extract fallback to rules: %s", e)
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
        resp = httpx.post(url, json=payload, timeout=_LLM_TIMEOUT)
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
        resp = httpx.post(url, headers=headers, json=payload, timeout=_LLM_TIMEOUT)
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
        resp = httpx.post(url, headers=headers, json=payload, timeout=_LLM_TIMEOUT)
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
