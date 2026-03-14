# routes/agent.py — Agent + Brain endpoints
import logging
from fastapi import APIRouter, Request
from brain import (
    instant_recommend,
    instant_recommend_by_category,
    regret_calculate,
    plan_trip,
)
from llm import agent_chat

router = APIRouter()

_MAX_HISTORY_TURNS = 20


@router.post("/api/brain")
async def api_brain(request: Request):
    """
    CardBrain 精算端點（直接精算，不經 LLM）。
    接受 {mode, merchant, amount, card_ids, transactions, destination, budget, breakdown}
    """
    body = await request.json()
    mode = body.get("mode")
    card_ids = body.get("card_ids")

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
    CardBrain Agent 端點 — Gemini Function Calling。
    接收 { message, history, card_ids }
    回傳 { reply, history, tool_results }
    """
    body = await request.json()
    message = body.get("message", "").strip()
    history = body.get("history")
    card_ids = body.get("card_ids")

    if not message:
        return {
            "reply": "請輸入你的消費情境，例如「星巴克 300」或「日本旅遊 10萬」",
            "history": history or [],
            "tool_results": [],
        }

    # 截斷 history（max 20 turns）
    if history and len(history) > _MAX_HISTORY_TURNS:
        history = history[-_MAX_HISTORY_TURNS:]

    result = agent_chat(message, history, card_ids)
    logging.info(
        "🧠 agent | input=%r | tools=%s | reply_len=%d",
        message,
        [t["name"] for t in result.get("tool_results", [])],
        len(result.get("reply", "")),
    )

    return result
