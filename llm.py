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
_LLM_TIMEOUT = 30  # 思考型模型（gemini-2.5-flash）需要更多時間

_SYSTEM_PROMPT = """你是 CardBrain 的意圖解析器。使用者會用中文自然語言描述消費或旅遊計畫。

你的唯一任務是分析輸入，並回傳純 JSON 格式，【絕對不要】包含任何說明文字或 Markdown 標籤。

■ 模式定義與 JSON 結構：

1. 單筆交易：
{"mode": "instant", "merchant": "商家名", "amount": 數字, "category": "分類"}

2. 多筆交易：
{"mode": "multi", "intents": [
  {"mode": "instant", "merchant": "商家A", "amount": 數字, "category": "分類"},
  {"mode": "instant", "merchant": "商家B", "amount": 數字, "category": "分類"}
]}

3. 旅遊計畫（明確包含機加酒的總預算）：
{"mode": "plan", "destination": "目的地", "budget": 數字, "breakdown": {"flights": 數字, "hotels": 數字, "shopping": 數字, "dining": 數字, "transport": 數字}}

4. 釐清問題（當提到旅遊，但未說明預算是否包含機票住宿時）：
{"mode": "clarify", "question": "請問這筆預算有包含事前購買機票和訂飯店的費用嗎？還是純粹在當地的實體花費呢？"}

■ Category 嚴格選項（擇一，無法判斷則設為 null）：
國內一般消費、海外消費、網購、行動支付、超商、超市、量販店、保費、繳稅、水電瓦斯、電信費、百貨公司、藥妝、寵物用品、咖啡店、速食、外送平台、餐廳、早餐店、加油、停車、大眾運輸、ETC、高鐵、影音串流、遊戲、電影院、訂房網站、航空公司、旅行社

■ 關鍵防呆規則（非常重要）：
- amount 必須是「純數字（整數）」。若無金額請設為 null。
- 若提到「多個商家」但只有「一個總金額」，請將金額平均分配給這些商家。
- 💡【旅遊情境判斷】：若使用者明確表示預算是「實體消費」、「當地花費」、「已經付完機加酒」，請【不要】使用 plan 模式，請直接改用 `instant` 模式，並將 category 設為「海外消費」。
- 💡【旅遊情境判斷】：若使用者只說「去XX玩帶多少錢」，未說明細節，請一律回傳 `clarify` 模式。
- 若輸入毫無意義，回傳 {"mode": "unknown"}。

■ 學習範例（Few-Shot Examples）：

範例 1（旅遊總預算，模糊不清）：
User: "我下個月要去日本玩五天，預算大概 8 萬元，推薦哪張卡？"
Output: {"mode": "clarify", "question": "請問這 8 萬元有包含事前購買機票和訂飯店的費用嗎？還是純粹在當地的花費呢？"}

範例 2（明確的當地實體消費）：
User: "機票跟住宿我都付完了，預計在日本當地實體消費會刷 5 萬元。"
Output: {"mode": "instant", "merchant": "日本當地", "amount": 50000, "category": "海外消費"}

範例 3（多商家共用金額）：
User: "我是網購族，每個月固定在蝦皮和 Momo 買東西，大概會花 15,000 元左右"
Output: {"mode": "multi", "intents": [{"mode": "instant", "merchant": "蝦皮", "amount": 7500, "category": "網購"}, {"mode": "instant", "merchant": "Momo", "amount": 7500, "category": "網購"}]}

範例 4（無金額的日常多筆消費）：
User: "我平常出門都用 LINE Pay，每天也會去 7-11 買咖啡，這樣要辦哪張卡？"
Output: {"mode": "multi", "intents": [{"mode": "instant", "merchant": "LINE Pay", "amount": null, "category": "行動支付"}, {"mode": "instant", "merchant": "7-11", "amount": null, "category": "超商"}]}

範例 5（多筆不同消費）：
User: "全聯2000加油200王品20000"
Output: {"mode": "multi", "intents": [{"mode": "instant", "merchant": "全聯", "amount": 2000, "category": "超市"}, {"mode": "instant", "merchant": "加油", "amount": 200, "category": "加油"}, {"mode": "instant", "merchant": "王品", "amount": 20000, "category": "餐廳"}]}

範例 6（無金額 + 有金額混合）：
User: "每天去 7-11 買咖啡，還有中油加油 2000"
Output: {"mode": "multi", "intents": [{"mode": "instant", "merchant": "7-11", "amount": null, "category": "超商"}, {"mode": "instant", "merchant": "中油", "amount": 2000, "category": "加油"}]}"""


_REPLY_SYSTEM_PROMPT = """你是 CardBrain 智慧刷卡助手。根據提供的精算結果，用親切的繁體中文回覆使用者。

⚠️ 絕對禁止：
- 禁止推薦精算結果以外的卡片，所有卡片名稱必須來自【關鍵數據】或【完整計算結果】
- 禁止編造回饋率、回饋金額等資訊。若數據中沒有省下金額（例如消費金額為 null），就只要推薦卡片，絕對不可編造金額。
- 「消費金額」和「回饋金額」絕對不要搞混。

⚠️ 必須做到：
- 金額用 $ 符號，保留小數點後一位，原封不動引用。
- 【多筆消費與網購】必須「逐項分開」列出，不可合併說明（例如：蝦皮歸蝦皮寫、Momo歸Momo寫）。

回覆格式要求（依模式）：
1. 釐清問題 (clarify)：直接原封不動回傳【關鍵數據】中的 question，語氣要像自然對話，不需要加其他廢話。
2. 單筆推薦 (instant)：
   - 說出你的最佳卡 + 回饋金額 + 回饋率。
   - 有第二推薦也要列。
   - 若有「更好選擇」必須提到辦哪張卡可多賺多少。
3. 多筆消費 (multi)：
   - 必須針對每一個商家「逐項」列出推薦卡片與回饋資訊（若無金額則只講回饋率與推薦理由）。
   - 若該商家有「更好選擇」，必須在該項目下方補充。
4. 旅遊規劃 (plan)：
   - 列出總預估省下金額。
   - 必須完整列出「逐類別明細」（直接引用數據中的「── 分類明細 ──」），包含分類、金額、卡片、回饋率與省下金額。
   - 若有「更好選擇」，逐項列出辦哪張新卡可多省多少。

語氣與格式：
- 先列出所有精算數據，最後加一句親切的話（clarify 模式除外）
- 不要用 markdown 格式，用純文字 + emoji，條理分明。"""


def generate_reply(mode: str, intent: dict, brain_result: dict) -> str:
    """
    將 brain 精算結果包裝成自然語言回覆。
    有 API key 時呼叫 LLM，否則用模板式 fallback。
    """
    if LLM_API_KEY and LLM_PROVIDER:
        try:
            return _llm_call_with_retry(_llm_reply, mode, intent, brain_result)
        except Exception as e:
            logging.warning("LLM reply fallback to template: %s", e)
    return _template_reply(mode, intent, brain_result)


def _build_reply_summary(mode: str, intent: dict, brain_result: dict) -> str:
    """將 brain_result 中最關鍵的數字預先整理成易讀摘要，避免 LLM 混淆。"""
    if mode == "clarify":
        return intent.get("question", "請問這筆預算有包含事前購買機票和訂飯店的費用嗎？還是純粹在當地的花費呢？")

    lines = []
    if mode == "instant":
        amount = brain_result.get("amount", intent.get("amount", 0))
        merchant = brain_result.get("merchant", intent.get("merchant", ""))
        lines.append(f"消費金額：${amount:,.0f}")
        if merchant:
            lines.append(f"商家：{merchant}")
        for i, r in enumerate(brain_result.get("results", [])[:3]):
            tag = "你的最佳卡片" if i == 0 else f"第{i+1}推薦"
            rtype = r.get("reward_type", "cashback")
            unit = "回饋" if rtype == "cashback" else ("哩程" if rtype == "miles" else "點")
            lines.append(f"{tag}：{r['bank_name']} {r['card_name']}，"
                         f"回饋 ${r.get('actual_reward', 0):,.1f} {unit}（{r.get('reward_rate', 0)}%）")
        better = brain_result.get("better_card")
        if better:
            lines.append(f"更好選擇：辦 {better['bank_name']} {better['card_name']} "
                         f"可得 ${better['actual_reward']:,.1f}（多賺 ${better['extra_reward']:,.1f}）")
    elif mode == "regret":
        lines.append(f"你的總回饋：${brain_result.get('total_your_reward', 0):,.1f}")
        lines.append(f"最佳總回饋：${brain_result.get('total_best_reward', 0):,.1f}")
        lines.append(f"少賺金額：${brain_result.get('total_regret', 0):,.1f}")
    elif mode == "plan":
        lines.append(f"目的地：{brain_result.get('destination', '')}")
        lines.append(f"預估總省下：${brain_result.get('total_savings', 0):,.1f}")
        # ── 分類明細 ──
        breakdown = brain_result.get("breakdown", [])
        if breakdown:
            lines.append("── 分類明細 ──")
            for b in breakdown:
                card = b.get("best_card", "無推薦")
                rate = b.get("best_rate", 0)
                lines.append(f"{b['category_label']} ${b['amount']:,.0f} → {card}（{rate}%）→ 省 ${b.get('savings', 0):,.1f}")
        # ── 帶卡清單 ──
        lines.append("── 帶卡清單 ──")
        for c in brain_result.get("cards_to_bring", [])[:3]:
            usage = "、".join(c.get("usage", []))
            lines.append(f"帶卡：{c['card']}（{usage}）")
        # ── 更好選擇 ──
        extra = brain_result.get("extra_if_upgrade", 0)
        if extra > 0:
            lines.append(f"── 更好選擇（多省 ${extra:,.1f}）──")
            for b in breakdown:
                bc = b.get("better_card")
                if bc:
                    lines.append(f"{b['category_label']}辦 {bc['card']}（{bc['rate']}%，多省 ${bc['extra']:,.1f}）")
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
                lines.append(f"你的最佳：{best['bank_name']} {best['card_name']}，"
                             f"回饋 ${best.get('actual_reward', 0):,.1f}（{best.get('reward_rate', 0)}%）")
                if len(results) > 1:
                    r2 = results[1]
                    lines.append(f"第2推薦：{r2['bank_name']} {r2['card_name']}，"
                                 f"回饋 ${r2.get('actual_reward', 0):,.1f}（{r2.get('reward_rate', 0)}%）")
            better = sub.get("better_card")
            if better:
                lines.append(f"更好選擇：辦 {better['bank_name']} {better['card_name']} "
                             f"可得 ${better['actual_reward']:,.1f}（多賺 ${better['extra_reward']:,.1f}）")
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
            "generationConfig": {"temperature": 0, "maxOutputTokens": 800},
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
    if mode == "clarify":
        return intent.get("question", "請問這筆預算有包含事前購買機票和訂飯店的費用嗎？還是純粹在當地的花費呢？")

    if "error" in brain_result:
        return f"抱歉，我無法處理這個查詢：{brain_result['error']}"

    if mode == "instant":
        results = brain_result.get("results", [])
        if not results:
            return "找不到符合的信用卡推薦，試試其他商家或金額？"
        best = results[0]
        merchant = brain_result.get("merchant", "該商家")
        amount = brain_result.get("amount", 0)
        reward = best.get("actual_reward", 0)
        rate = best.get("reward_rate", 0)
        rtype = best.get("reward_type", "cashback")
        unit = "回饋" if rtype == "cashback" else ("哩程" if rtype == "miles" else "點")
        reply = f"在{merchant}消費 ${amount:,.0f}，推薦使用 {best['bank_name']} {best['card_name']}"
        reply += f"\n可獲得 ${reward:,.1f} {unit}（{rate}%）"
        if len(results) > 1:
            r2 = results[1]
            reply += f"\n第二推薦：{r2['bank_name']} {r2['card_name']}（${r2.get('actual_reward', 0):,.1f}）"
        better = brain_result.get("better_card")
        if better:
            reply += f"\n💡 辦 {better['bank_name']} {better['card_name']} 可得 ${better['actual_reward']:,.1f}，多賺 ${better['extra_reward']:,.1f}！"
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
        extra = brain_result.get("extra_if_upgrade", 0)
        if extra > 0:
            for b in brain_result.get("breakdown", []):
                bc = b.get("better_card")
                if bc:
                    reply += f"\n💡 {b['category_label']}辦 {bc['card']}（{bc['rate']}%，多省 ${bc['extra']:,.1f}）"
            reply += f"\n全部升級可多省 ${extra:,.1f}"
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
            better = sub.get("better_card")
            if better:
                parts.append(f"  💡 辦 {better['bank_name']} {better['card_name']} 可多賺 ${better['extra_reward']:,.1f}")
        return "\n".join(parts)

    return "已收到你的查詢，但我不確定該如何回覆。請試試輸入商家+金額，或旅遊目的地+預算。"


def _llm_call_with_retry(fn, *args, max_retries=2):
    """LLM 呼叫 + 429 自動重試。"""
    import time
    for attempt in range(max_retries + 1):
        try:
            return fn(*args)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise


def extract_intent(user_input: str) -> dict:
    """
    解析自然語言意圖。有 LLM API key 時用 LLM，否則降級為規則式解析。
    """
    if LLM_API_KEY and LLM_PROVIDER:
        try:
            return _llm_call_with_retry(_llm_extract, user_input)
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
    result = json.loads(text)
    # LLM 有時回傳陣列 [{...}] 而非物件 {...}，取第一個元素
    if isinstance(result, list):
        if len(result) > 0 and isinstance(result[0], dict):
            return result[0]
        return {"mode": "unknown"}
    if not isinstance(result, dict):
        return {"mode": "unknown"}
    return result


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
_TRAVEL_KEYWORDS = ["旅遊", "出國", "旅行", "行程", "自由行", "跟團", "玩"]
_DESTINATIONS = [
    # 海外
    "日本", "韓國", "泰國", "歐洲", "美國", "東京", "大阪", "京都",
    "首爾", "曼谷", "沖繩", "北海道", "新加坡", "馬來西亞", "越南",
    "香港", "澳門", "澳洲", "紐西蘭", "英國", "法國", "德國",
    "加拿大", "夏威夷", "峇里島", "長灘島",
    # 國內
    "花蓮", "台東", "台南", "高雄", "墾丁", "宜蘭", "日月潭",
    "阿里山", "澎湖", "金門", "馬祖", "綠島", "蘭嶼", "台中",
    "嘉義", "苗栗", "南投", "屏東", "小琉球",
]

# 金額 pattern：支援 "300", "300元", "2000塊", "10萬", "3.5萬", "15,000"
_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*萬")
_AMOUNT_COMMA_RE = re.compile(r"(\d{1,3}(?:,\d{3})+)\s*(?:元|塊)?")
# (?<![-\-]) 防止 "7-11" 的 "11" 被抓為金額
_AMOUNT_SIMPLE_RE = re.compile(r"(?<![-\-])(\d{2,})\s*(?:元|塊)?(?=\s|$|[，,。！？\u4e00-\u9fff])")

# 中文數字解析
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "兩": 2}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000, "萬": 10000}
_CN_AMOUNT_RE = re.compile(r"([一二三四五六七八九十百千萬兩]{2,})(?:元|塊)?")


def _cn_to_number(text: str) -> int:
    """中文數字轉阿拉伯數字。支援「五百」「三千五」「兩萬」「一萬五千」等。"""
    result = 0
    current = 0
    last_unit = 1
    for char in text:
        if char in _CN_DIGITS:
            current = _CN_DIGITS[char]
        elif char in _CN_UNITS:
            unit = _CN_UNITS[char]
            if unit == 10000:
                result = (result + (current or 1)) * 10000
                current = 0
            else:
                result += (current or 1) * unit
                current = 0
            last_unit = unit
    # 尾數簡寫：「三千五」= 3500（五 × 千/10）
    if current > 0:
        if last_unit >= 100:
            result += current * (last_unit // 10)
        else:
            result += current
    return result if result > 0 else current


def _extract_all_pairs(text: str) -> list[dict]:
    """從文字中提取所有 商家+金額 配對。找到幾組就回傳幾筆。"""
    # 找出所有金額及其位置（阿拉伯數字 + 中文數字）
    amount_matches = []
    for m in _AMOUNT_RE.finditer(text):
        amount_matches.append((m.start(), m.end(), float(m.group(1)) * 10000))
    for m in _AMOUNT_COMMA_RE.finditer(text):
        if not any(a[0] <= m.start() < a[1] for a in amount_matches):
            amount_matches.append((m.start(), m.end(), float(m.group(1).replace(",", ""))))
    for m in _AMOUNT_SIMPLE_RE.finditer(text):
        if not any(a[0] <= m.start() < a[1] for a in amount_matches):
            amount_matches.append((m.start(), m.end(), float(m.group(1))))
    for m in _CN_AMOUNT_RE.finditer(text):
        if not any(a[0] <= m.start() < a[1] for a in amount_matches):
            val = _cn_to_number(m.group(1))
            if val >= 10:
                amount_matches.append((m.start(), m.end(), float(val)))

    if len(amount_matches) < 2:
        return []

    amount_matches.sort(key=lambda x: x[0])

    results = []
    for i, (start, _end, amount) in enumerate(amount_matches):
        seg_start = amount_matches[i - 1][1] if i > 0 else 0
        segment = text[seg_start:start]
        merchant = _extract_merchant(segment)
        category = _guess_category(merchant or "") or _guess_category(segment)
        intent = {"mode": "instant", "amount": amount}
        if merchant:
            intent["merchant"] = merchant
        if category:
            intent["category"] = category
        results.append(intent)

    return results


def _extract_shared_amount_merchants(text: str) -> list[dict] | None:
    """
    偵測「A 和/跟/與 B（共用金額）」的模式。
    例如「蝦皮和 Momo 15000」→ 兩筆各 7500。
    """
    # 從 _CATEGORY_KEYWORDS 收集已知商家名稱（排除分類名稱本身，如「網購」「加油」）
    _GENERIC_KEYWORDS = set(_CATEGORY_KEYWORDS.keys())  # 分類名稱不是真正的商家
    all_merchants = []
    for keywords in _CATEGORY_KEYWORDS.values():
        for kw in keywords:
            if kw not in _GENERIC_KEYWORDS:
                all_merchants.append(kw)

    # 尋找文字中出現的所有已知商家
    lower = text.lower()
    found = []
    for m in all_merchants:
        ml = m.lower()
        pos = lower.find(ml)
        if pos >= 0:
            # 避免子字串重複（如 "line pay" 和 "pay"），取最長的
            overlap = False
            for _, fm, fp in found:
                if abs(pos - fp) < max(len(m), len(fm)) and len(m) < len(fm):
                    overlap = True
                    break
            if not overlap:
                # 移除被新的更長匹配覆蓋的舊匹配
                found = [(p, n, fp) for p, n, fp in found
                         if not (abs(pos - fp) < max(len(m), len(n)) and len(n) < len(m))]
                found.append((pos, m, pos))

    if len(found) < 2:
        return None

    # 檢查商家之間是否有「和」「跟」「與」「還有」「以及」連接
    found.sort(key=lambda x: x[0])
    between = text[found[0][0] + len(found[0][1]):found[-1][0]]
    connectors = ["和", "跟", "與", "還有", "以及", "、"]
    has_connector = any(c in between for c in connectors)
    if not has_connector:
        return None

    # 提取金額
    amount = _extract_amount(text)
    if not amount:
        return None

    # 平分金額
    merchants = [(f[1], f[0]) for f in found]
    per_amount = round(amount / len(merchants))
    intents = []
    for merchant_name, _ in merchants:
        category = _guess_category(merchant_name)
        intent = {"mode": "instant", "merchant": merchant_name, "amount": per_amount}
        if category:
            intent["category"] = category
        intents.append(intent)

    return intents


def _rule_extract(user_input: str) -> dict:
    """規則式意圖解析。自動偵測多筆交易。"""
    text = user_input.strip()

    # 嘗試多筆配對提取（找到 2+ 組金額就拆成多筆）
    pairs = _extract_all_pairs(text)
    if len(pairs) > 1:
        return {"mode": "multi", "intents": pairs}

    # 嘗試「多商家共用金額」（A 和 B 共 15000）
    shared = _extract_shared_amount_merchants(text)
    if shared and len(shared) > 1:
        return {"mode": "multi", "intents": shared}

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

    # 找逗號分隔數字（15,000）
    m = _AMOUNT_COMMA_RE.search(text)
    if m:
        return float(m.group(1).replace(",", ""))

    # 再找普通數字
    m = _AMOUNT_SIMPLE_RE.search(text)
    if m:
        return float(m.group(1))

    # 最後找中文數字（五百、三千、兩萬…）
    m = _CN_AMOUNT_RE.search(text)
    if m:
        val = _cn_to_number(m.group(1))
        if val >= 10:
            return float(val)

    return None


def _extract_merchant(text: str) -> str | None:
    """從文字中提取商家名稱（移除金額和常見詞後的剩餘部分）。"""
    cleaned = text
    # 移除金額相關（阿拉伯 + 中文數字）
    cleaned = _AMOUNT_RE.sub("", cleaned)
    cleaned = _AMOUNT_COMMA_RE.sub("", cleaned)
    cleaned = _AMOUNT_SIMPLE_RE.sub("", cleaned)
    cleaned = _CN_AMOUNT_RE.sub("", cleaned)
    # 移除常見動詞、介詞、時間詞
    for word in ["在", "去", "到", "花", "刷", "買", "吃", "喝", "消費", "結帳", "付",
                  "我", "了", "的", "是", "有", "和", "跟", "還有", "以及",
                  "之後", "然後", "接著", "再", "又", "先",
                  "預計", "大概", "大約", "左右", "元", "塊",
                  "等一下", "最後", "準備", "要", "可能", "東西", "一些",
                  "每個月", "固定", "通常", "都", "會", "大概會",
                  "網購族", "哪張卡", "哪張", "現金回饋", "回饋", "最划算", "划算"]:
        cleaned = cleaned.replace(word, " ")
    # 移除數字
    cleaned = re.sub(r"\d+", "", cleaned)
    # 清理空白
    cleaned = cleaned.strip()
    # 取第一個有意義的詞（至少包含中文或英文字母）
    parts = [p.strip() for p in re.split(r"[\s，,。、；;]+", cleaned) if p.strip()]
    for p in parts:
        if re.search(r"[\u4e00-\u9fffa-zA-Z]", p):
            return p
    return None
