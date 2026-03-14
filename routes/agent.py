# routes/agent.py — Agent + Brain endpoints
import logging
from fastapi import APIRouter, Request
from brain import (
    instant_recommend,
    instant_recommend_by_category,
    regret_calculate,
    plan_trip,
)
from llm import extract_intent, generate_reply

router = APIRouter()


@router.post("/api/brain")
async def api_brain(request: Request):
    """
    CardBrain 3.0 精算端點。
    接受 {mode, query, merchant, amount, card_ids, transactions, destination, budget, breakdown}
    """
    body = await request.json()
    mode = body.get("mode")
    query = body.get("query")
    card_ids = body.get("card_ids")

    # 若有自然語言 query，經過意圖萃取補齊 merchant/amount 等欄位
    if query:
        intent = extract_intent(query)
        # 合併 intent 到 body（body 中已有的欄位優先）
        for k, v in intent.items():
            if k not in body or body[k] is None:
                body[k] = v
        if not mode:
            mode = body.get("mode", "instant")

    if mode == "instant":
        return _handle_instant(body, card_ids)
    elif mode == "regret":
        return _handle_regret(body, card_ids)
    elif mode == "plan":
        return _handle_plan(body, card_ids)
    else:
        return {"error": "Unknown mode. Use: instant, regret, plan"}


def _handle_instant(body: dict, card_ids: list[int] | None) -> dict:
    merchant = body.get("merchant")
    amount = body.get("amount", 0)
    category_id = body.get("category_id")
    category = body.get("category")

    if not amount:
        return {"error": "amount is required for instant mode"}

    if category_id:
        return instant_recommend_by_category(category_id, float(amount), card_ids)
    elif merchant:
        return instant_recommend(merchant, float(amount), card_ids, category=category)
    elif category:
        return instant_recommend(category, float(amount), card_ids, category=category)
    else:
        return {"error": "merchant or category_id is required"}


def _handle_regret(body: dict, card_ids: list[int] | None) -> dict:
    transactions = body.get("transactions", [])
    if not transactions:
        return {"error": "transactions is required for regret mode"}
    return regret_calculate(transactions, card_ids)


def _handle_plan(body: dict, card_ids: list[int] | None) -> dict:
    destination = body.get("destination", "")
    budget = body.get("budget", 0)
    breakdown = body.get("breakdown")

    if not destination:
        return {"error": "destination is required for plan mode"}
    if not budget and not breakdown:
        return {"error": "budget or breakdown is required for plan mode"}

    return plan_trip(destination, float(budget), breakdown, card_ids)


@router.post("/api/agent")
async def api_agent(request: Request):
    """
    CardBrain Agent 端點。
    接收 { message: "星巴克 300", card_ids: [1,5] }
    回傳 { reply: "人話回覆", mode: "instant", data: {精算結果} }
    """
    body = await request.json()
    message = body.get("message", "").strip()
    card_ids = body.get("card_ids")

    if not message:
        return {"reply": "請輸入你的消費情境，例如「星巴克 300」或「日本旅遊 10萬」", "mode": None, "data": None}

    # 1. 意圖解析
    intent = extract_intent(message)
    mode = intent.get("mode", "instant")
    logging.info("🧠 intent | input=%r | mode=%s | result=%s", message, mode, intent)

    # 無法辨識的輸入 → 直接回傳引導訊息，不呼叫 brain
    if mode == "unknown":
        return {
            "reply": "我是刷卡推薦助手 💳 請輸入消費情境，例如「星巴克 300」或「日本旅遊 10萬」",
            "mode": None,
            "data": None,
        }

    # 2. 呼叫精算引擎
    if mode == "multi":
        items = []
        for sub_intent in intent.get("intents", []):
            sub_input = {**sub_intent, "card_ids": card_ids}
            sub_mode = sub_intent.get("mode", "instant")
            if sub_mode == "instant":
                sub_data = _handle_instant(sub_input, card_ids)
            elif sub_mode == "plan":
                sub_data = _handle_plan(sub_input, card_ids)
            else:
                continue
            items.append({"mode": sub_mode, "intent": sub_intent, "data": sub_data})
        data = {"items": items}
    else:
        brain_input = {**intent, "card_ids": card_ids}
        if mode == "instant":
            data = _handle_instant(brain_input, card_ids)
        elif mode == "regret":
            data = _handle_regret(brain_input, card_ids)
        elif mode == "plan":
            data = _handle_plan(brain_input, card_ids)
        else:
            data = {"error": "Unknown mode"}

    # 3. 生成自然語言回覆
    reply = generate_reply(mode, intent, data)
    logging.info("🧠 brain  | mode=%s | data_keys=%s", mode, list(data.keys()) if isinstance(data, dict) else "N/A")

    return {"reply": reply, "mode": mode, "data": data}
