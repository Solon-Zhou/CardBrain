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
  "category": "消費分類（若能判斷，從下方列表中選擇）",
  "destination": "目的地（若為旅遊）",
  "budget": 數字（旅遊總預算）,
  "breakdown": {"flights": 數字, "hotels": 數字, "shopping": 數字, "dining": 數字, "transport": 數字}
}

category 必須從以下選項中選擇（若無法判斷則省略）：
國內一般消費、海外消費、網購、行動支付、超商、超市、量販店、
保費、繳稅、水電瓦斯、電信費、
百貨公司、藥妝、寵物用品、
咖啡店、速食、外送平台、餐廳、早餐店、
加油、停車、大眾運輸、ETC、高鐵、
影音串流、遊戲、電影院、
訂房網站、航空公司、旅行社

規則：
- 提到商家+金額 → mode=instant
- 提到旅遊/出國/目的地 → mode=plan
- 只有商家沒有金額 → mode=instant, amount=null
- 預算若只有總額，按 30/25/25/10/10 比例拆分 breakdown
- 若輸入不像消費或旅遊相關的有意義文字（如亂碼、符號、無意義字串），回傳 {"mode": "unknown"}
- 只回傳 JSON，不要其他文字"""


_REPLY_SYSTEM_PROMPT = """你是 CardBrain 智慧刷卡助手。根據提供的精算結果，用親切的繁體中文回覆使用者。

⚠️ 最重要規則 — 數字精確度：
- 訊息開頭會有【關鍵數據】區塊，裡面的金額必須原封不動使用，禁止自行換算或省略位數
- 「消費金額」和「回饋金額」是完全不同的數字，絕對不要搞混
- 例：消費 $1,000 回饋 $12.0 → 不可以寫成「消費 $12」或「消費 $10」

其他規則：
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


def _build_reply_summary(mode: str, intent: dict, brain_result: dict) -> str:
    """將 brain_result 中最關鍵的數字預先整理成易讀摘要，避免 LLM 混淆。"""
    lines = []
    if mode == "instant":
        amount = brain_result.get("amount", intent.get("amount", 0))
        merchant = brain_result.get("merchant", intent.get("merchant", ""))
        lines.append(f"消費金額：${amount:,.0f}")
        if merchant:
            lines.append(f"商家：{merchant}")
        for i, r in enumerate(brain_result.get("results", [])[:3]):
            tag = "最佳推薦" if i == 0 else f"第{i+1}推薦"
            rtype = r.get("reward_type", "cashback")
            unit = "回饋" if rtype == "cashback" else ("哩程" if rtype == "miles" else "點")
            lines.append(f"{tag}：{r['bank_name']} {r['card_name']}，"
                         f"回饋 ${r.get('actual_reward', 0):,.1f} {unit}（{r.get('reward_rate', 0)}%）")
    elif mode == "regret":
        lines.append(f"你的總回饋：${brain_result.get('total_your_reward', 0):,.1f}")
        lines.append(f"最佳總回饋：${brain_result.get('total_best_reward', 0):,.1f}")
        lines.append(f"少賺金額：${brain_result.get('total_regret', 0):,.1f}")
    elif mode == "plan":
        lines.append(f"目的地：{brain_result.get('destination', '')}")
        lines.append(f"預估總省下：${brain_result.get('total_savings', 0):,.1f}")
        for c in brain_result.get("cards_to_bring", [])[:3]:
            usage = "、".join(c.get("usage", []))
            lines.append(f"帶卡：{c['card']}（{usage}）")
    elif mode == "multi":
        for item in brain_result.get("items", []):
            sub = item.get("data", {})
            sub_intent = item.get("intent", {})
            merchant = sub.get("merchant", sub_intent.get("merchant", ""))
            amount = sub.get("amount", sub_intent.get("amount", 0))
            results = sub.get("results", [])
            best = results[0] if results else None
            lines.append(f"{'─' * 10}")
            lines.append(f"消費：{merchant} ${amount:,.0f}")
            if best:
                lines.append(f"推薦：{best['bank_name']} {best['card_name']}，"
                             f"回饋 ${best.get('actual_reward', 0):,.1f}（{best.get('reward_rate', 0)}%）")
    return "\n".join(lines)


def _llm_reply(mode: str, intent: dict, brain_result: dict) -> str:
    import httpx

    summary = _build_reply_summary(mode, intent, brain_result)
    user_msg = (
        f"【關鍵數據（必須精確引用）】\n{summary}\n\n"
        f"【完整計算結果】\n"
        f"{json.dumps({'mode': mode, 'intent': intent, 'result': brain_result}, ensure_ascii=False)}"
    )

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

    elif mode == "multi":
        items = brain_result.get("items", [])
        if not items:
            return "找不到符合的信用卡推薦，試試其他商家或金額？"
        parts = []
        for item in items:
            sub = item.get("data", {})
            sub_intent = item.get("intent", {})
            merchant = sub.get("merchant", sub_intent.get("merchant", ""))
            amount = sub.get("amount", sub_intent.get("amount", 0))
            results = sub.get("results", [])
            best = results[0] if results else None
            if best:
                reward = best.get("actual_reward", 0)
                rate = best.get("reward_rate", 0)
                parts.append(f"在{merchant}消費 ${amount:,.0f}，推薦 {best['bank_name']} {best['card_name']}（{rate}%，回饋 ${reward:,.1f}）")
            else:
                parts.append(f"在{merchant}消費 ${amount:,.0f}，找不到特別推薦")
        return "\n".join(parts)

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

# ── 分類關鍵字映射（key = DB categories.name） ────────
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "咖啡店": ["咖啡", "星巴克", "路易莎", "cama", "伯朗"],
    "餐廳": ["餐廳", "牛排", "火鍋", "燒肉", "燒烤", "壽司", "拉麵", "義大利麵",
             "王品", "鼎泰豐", "瓦城", "鬍鬚張", "吉野家", "爭鮮", "三商巧福",
             "石二鍋", "饗食天堂", "欣葉"],
    "速食": ["速食", "麥當勞", "肯德基", "漢堡王", "摩斯", "頂呱呱", "必勝客",
             "達美樂", "拿坡里"],
    "早餐店": ["早餐", "美而美", "拉亞", "麥味登", "蛋餅", "豆漿"],
    "超商": ["超商", "便利商店", "7-11", "711", "全家", "familymart", "萊爾富", "ok超商"],
    "超市": ["超市", "全聯", "家樂福", "頂好", "美聯社"],
    "量販店": ["量販", "好市多", "costco", "大潤發", "愛買"],
    "百貨公司": ["百貨", "sogo", "新光三越", "遠百", "微風", "統一時代", "大遠百"],
    "藥妝": ["藥妝", "屈臣氏", "康是美", "寶雅", "日藥本舖"],
    "外送平台": ["外送", "ubereats", "uber eats", "foodpanda", "熊貓"],
    "網購": ["網購", "蝦皮", "momo", "pchome", "博客來", "amazon"],
    "行動支付": ["行動支付", "linepay", "line pay", "街口", "台灣pay", "悠遊付",
                 "icash pay", "全盈pay", "pi錢包"],
    "加油": ["加油", "中油", "台塑", "加油站"],
    "停車": ["停車", "停車場", "停車費"],
    "大眾運輸": ["捷運", "公車", "客運", "悠遊卡"],
    "高鐵": ["高鐵", "台灣高鐵"],
    "ETC": ["etc", "etag", "國道", "過路費"],
    "影音串流": ["netflix", "spotify", "disney+", "youtube premium", "串流",
                 "kkbox", "apple music"],
    "遊戲": ["遊戲", "steam", "playstation", "nintendo", "xbox"],
    "電影院": ["電影", "影城", "威秀", "秀泰", "國賓"],
    "保費": ["保費", "保險"],
    "繳稅": ["繳稅", "所得稅", "房屋稅", "牌照稅"],
    "水電瓦斯": ["水費", "電費", "瓦斯", "水電"],
    "電信費": ["電信", "中華電信", "遠傳", "台灣大", "台哥大", "月租"],
    "訂房網站": ["訂房", "agoda", "booking", "hotels.com", "airbnb"],
    "航空公司": ["機票", "航空", "華航", "長榮", "星宇", "虎航"],
    "旅行社": ["旅行社", "雄獅", "東南旅行", "可樂旅遊", "klook", "kkday"],
    "寵物用品": ["寵物", "毛小孩"],
    "綠色消費": ["綠色消費", "碳權"],
    "電動車充電": ["充電樁", "電動車充電"],
}


def _guess_category(text: str) -> str | None:
    """關鍵字匹配 → DB category name 或 None。"""
    if not text:
        return None
    lower = text.lower()
    for cat_name, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower:
                return cat_name
    return None


# 旅遊關鍵字
_TRAVEL_KEYWORDS = ["旅遊", "出國", "旅行", "行程", "自由行", "跟團"]
_DESTINATIONS = ["日本", "韓國", "泰國", "歐洲", "美國", "東京", "大阪", "京都", "首爾", "曼谷", "沖繩", "北海道"]

# 金額 pattern：支援 "300", "300元", "2000塊", "10萬", "3.5萬"
_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*萬")
_AMOUNT_SIMPLE_RE = re.compile(r"(\d{2,})\s*(?:元|塊)?(?=\s|$|[，,。！？\u4e00-\u9fff])")


# 複合句連接詞 pattern（「之後」「然後」「接著」「又去」「再去」）
_COMPOUND_RE = re.compile(r"[，,；]?\s*(?:之後|然後|接著)(?:再|又)?(?:去)?|[，,；]\s*(?:再去|又去)")


def _split_compound(text: str) -> list[str]:
    """用連接詞拆分複合句。僅在有明確連接詞時拆分。"""
    parts = _COMPOUND_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _rule_extract(user_input: str) -> dict:
    """規則式意圖解析。支援複合句拆分為多筆交易。"""
    text = user_input.strip()

    # 嘗試複合句拆分
    parts = _split_compound(text)
    if len(parts) > 1:
        intents = [_rule_extract_single(p) for p in parts]
        intents = [i for i in intents if i.get("mode") != "unknown"]
        if len(intents) > 1:
            return {"mode": "multi", "intents": intents}
        if len(intents) == 1:
            return intents[0]
        return {"mode": "unknown"}

    return _rule_extract_single(text)


def _rule_extract_single(text: str) -> dict:
    """單句意圖解析：regex 提取商家名 + 金額 + 旅遊關鍵字。"""
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

    # 分類猜測：先用 merchant（更精確），再用完整 text（兜底「加油 2000」情境）
    category = _guess_category(merchant or "") or _guess_category(text)
    if category:
        result["category"] = category

    # 若既沒有商家也沒有金額也沒有分類，視為無法辨識
    if not merchant and not amount and not category:
        return {"mode": "unknown"}

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

    return None


def _extract_merchant(text: str) -> str | None:
    """從文字中提取商家名稱（移除金額和常見詞後的剩餘部分）。"""
    cleaned = text
    # 移除金額相關
    cleaned = _AMOUNT_RE.sub("", cleaned)
    cleaned = _AMOUNT_SIMPLE_RE.sub("", cleaned)
    # 移除常見動詞和介詞
    for word in ["在", "去", "到", "花", "刷", "買", "吃", "喝", "消費", "結帳", "付",
                  "我", "了", "之後", "然後", "接著", "再", "又", "先", "跟"]:
        cleaned = cleaned.replace(word, " ")
    # 移除數字
    cleaned = re.sub(r"\d+", "", cleaned)
    # 清理空白
    cleaned = cleaned.strip()
    # 取第一個有意義的詞（至少包含中文或英文字母）
    parts = [p.strip() for p in re.split(r"[\s，,。]+", cleaned) if p.strip()]
    for p in parts:
        if re.search(r"[\u4e00-\u9fffa-zA-Z]", p):
            return p
    return None
