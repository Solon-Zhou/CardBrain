"""
CardBrain 4.0 — Gemini Function Calling Agent
LLM 直接決定呼叫哪個 tool，天生具備追問能力和多輪對話支援。
"""

import json
import logging
import os
import time

import httpx

# ── 設定（動態讀取，避免 module import 時 .env 尚未注入）──────────────────────
def _api_key() -> str:
    return os.getenv("LLM_API_KEY", "")

def _llm_model() -> str:
    return os.getenv("LLM_MODEL", "gemini-2.5-flash")

_LLM_TIMEOUT = 30

# ── Agent System Prompt ──────────────────────────
_AGENT_SYSTEM_PROMPT = """你是 CardBrain 智慧刷卡助手。你的任務是幫助使用者找到最划算的信用卡。

■ 你擁有的工具：
1. instant_recommend — 查詢單筆消費的最佳卡片（給商家名、金額、分類）
2. plan_trip — 旅遊行程規劃（給目的地、總預算、各類別金額拆分）
3. regret_calculate — 後悔計算機（比較已用的卡 vs 最佳卡的差距）

■ 使用規則：
- 使用者提到「多個商家 + 各自金額」→ 分別呼叫多次 instant_recommend（每個商家一次）
- 使用者提到「多個商家 + 一個總金額」→ 將金額平均分配，分別呼叫 instant_recommend
- 使用者只說「去XX玩帶多少錢」但沒說預算含不含機加酒 → 不要呼叫工具，直接反問：「請問這筆預算有包含事前購買機票和訂飯店的費用嗎？還是純粹在當地的實體花費呢？」
- 使用者說預算「包含機加酒」→ 呼叫 plan_trip
- 使用者說「機票住宿付完了 / 當地消費 / 實體花費」→ 呼叫 instant_recommend，category 設為「海外消費」
- 若使用者輸入跟信用卡或消費無關 → 不呼叫工具，友善引導他輸入消費情境
- 當使用者說「那XX呢？」之類的追問，根據對話歷史理解上下文，推斷消費金額與商家

■ 外幣辨識規則：
- 若使用者提到外幣金額，呼叫工具時必須帶上 currency 欄位（ISO 4217 代碼）
- 日幣/日圓 → JPY，美金/美元 → USD，港幣 → HKD，歐元 → EUR，英鎊 → GBP，
  韓元/韓幣 → KRW，澳幣 → AUD，新幣/新加坡幣 → SGD，泰銖/泰幣 → THB
- amount 欄位傳「原始外幣金額」，禁止自行換算
- 若工具結果含 fx_conversion 欄位，回覆格式如下：
  1. 先顯示 fx_conversion.display_text（匯率換算資訊）
  2. 列出各卡「回饋」金額（直接來自工具回傳，不做任何扣除）
  3. 顯示 fx_conversion.fee_text（手續費提示）
  4. 顯示「📊 實際淨回饋：」區塊，逐卡列出「回饋 - fx_conversion.fee_amount」的結果
  範例：「🌏 6000 JPY = 1264.2 TWD（匯率 0.2107）

💳 你的最佳卡（回饋）：
FlyGo 卡 5% 海外 → $63.2
Other 卡 3% 海外 → $37.9

⚠️ 海外手續費 1.5% = $18.96

📊 實際淨回饋：
FlyGo 卡 → $44.2
Other 卡 → $18.9」

■ Category 選項（擇一，無法判斷則不填）：
國內一般消費、海外消費、網購、行動支付、超商、超市、量販店、保費、繳稅、水電瓦斯、電信費、百貨公司、藥妝、寵物用品、咖啡店、速食、外送平台、餐廳、早餐店、加油、停車、大眾運輸、ETC、高鐵、影音串流、遊戲、電影院、訂房網站、航空公司、旅行社

■ 回覆格式：
- 用親切的繁體中文回覆
- 金額用 $ 符號，保留小數點後一位，精確引用工具回傳的數字
- 多筆消費必須逐項分開列出
- 不要用 markdown 格式，用純文字 + emoji
- 先列精算數據，最後加一句親切的話
- 禁止編造回饋率或金額，所有數字必須來自工具回傳結果
- 消費金額和回饋金額絕對不要搞混

■ 重要：區分「用戶擁有的卡」和「辦卡推薦」
- 工具回傳的 user_owned_cards 是用戶已經擁有的卡片，先推薦這些
- 工具回傳的 better_card_not_owned 是用戶「沒有」但回饋更好的卡，要另外標示為「辦卡推薦」
- 回覆時必須先說「你的最佳卡：XXX」，再說「如果辦 XXX 可以多賺 $XX」
- 絕對不要把兩者混在一起排名"""

# ── Tool Declarations ────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "instant_recommend",
        "description": "查詢單筆消費的最佳信用卡推薦。回傳按回饋金額排序的卡片清單。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "merchant_name": {
                    "type": "STRING",
                    "description": "商家名稱，例如「星巴克」、「全聯」、「日本當地」",
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "消費金額（新台幣），例如 300、2000。若使用者未提供金額則不要填。",
                },
                "category": {
                    "type": "STRING",
                    "description": "消費分類，例如「咖啡店」、「超市」、「海外消費」、「網購」。可不填，系統會自動判斷。",
                },
                "currency": {
                    "type": "STRING",
                    "description": "消費貨幣的 ISO 4217 代碼，例如 JPY、USD、EUR。台幣可省略。",
                },
            },
            "required": ["merchant_name"],
        },
    },
    {
        "name": "plan_trip",
        "description": "旅遊行程規劃，依消費類別各自找最佳卡片並計算預估總回饋。適用於預算包含機票住宿的情境。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "destination": {
                    "type": "STRING",
                    "description": "旅遊目的地，例如「日本」、「韓國」、「花蓮」",
                },
                "total_budget": {
                    "type": "NUMBER",
                    "description": "總預算金額（新台幣）",
                },
                "budget_currency": {
                    "type": "STRING",
                    "description": "total_budget 的貨幣代碼，例如 JPY。台幣可省略。",
                },
                "breakdown": {
                    "type": "OBJECT",
                    "description": "各類別金額拆分，key 為 flights/hotels/shopping/dining/transport",
                    "properties": {
                        "flights": {"type": "NUMBER", "description": "機票費用"},
                        "hotels": {"type": "NUMBER", "description": "住宿費用"},
                        "shopping": {"type": "NUMBER", "description": "購物費用"},
                        "dining": {"type": "NUMBER", "description": "餐飲費用"},
                        "transport": {"type": "NUMBER", "description": "交通費用"},
                    },
                },
            },
            "required": ["destination", "total_budget"],
        },
    },
    {
        "name": "regret_calculate",
        "description": "後悔計算機：比較多筆交易中使用者實際用的卡 vs 最佳卡的回饋差距。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "transactions": {
                    "type": "ARRAY",
                    "description": "交易列表",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "merchant": {"type": "STRING", "description": "商家名稱"},
                            "amount": {"type": "NUMBER", "description": "消費金額"},
                            "card_id": {"type": "INTEGER", "description": "使用的卡片 ID"},
                        },
                        "required": ["merchant", "amount", "card_id"],
                    },
                },
            },
            "required": ["transactions"],
        },
    },
]


def _call_with_retry(fn, *args, max_retries=2):
    """LLM 呼叫 + 429 自動重試。"""
    for attempt in range(max_retries + 1):
        try:
            return fn(*args)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise


def _gemini_request(contents: list, include_tools: bool = True) -> dict:
    """封裝 Gemini REST API 呼叫。"""
    model = _llm_model()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={_api_key()}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": _AGENT_SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0, "maxOutputTokens": 1000},
    }
    if include_tools:
        payload["tools"] = [{"function_declarations": TOOL_DECLARATIONS}]

    resp = httpx.post(url, json=payload, timeout=_LLM_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _execute_tool(
    name: str, args: dict, user_card_ids: list[int] | None
) -> dict:
    """分派到 brain 函數，並在必要時做外幣換算。"""
    from brain import instant_recommend, plan_trip, regret_calculate
    from exchange import convert_to_twd

    try:
        if name == "instant_recommend":
            merchant = args.get("merchant_name", "")
            amount = args.get("amount") or 0
            category = args.get("category")
            currency = args.get("currency", "TWD")

            fx_info = convert_to_twd(float(amount), currency)
            # brain.py 只接受不含手續費的台幣金額
            result = instant_recommend(merchant, fx_info["base_twd"], user_card_ids, category=category)
            if fx_info["is_foreign"]:
                result["fx_conversion"] = fx_info
            return result

        elif name == "plan_trip":
            destination = args.get("destination", "")
            total_budget = args.get("total_budget", 0)
            breakdown = args.get("breakdown")
            budget_currency = args.get("budget_currency", "TWD")

            fx_info = convert_to_twd(float(total_budget), budget_currency)
            # breakdown 按匯率換算（直接用 rate_to_twd，避免 base_twd round 誤差與除零）
            if fx_info["is_foreign"] and breakdown:
                rate = fx_info["rate_to_twd"]
                breakdown = {k: round(v * rate, 2) for k, v in breakdown.items()}
            result = plan_trip(destination, fx_info["base_twd"], breakdown, user_card_ids)
            if fx_info["is_foreign"]:
                result["fx_conversion"] = fx_info
            return result

        elif name == "regret_calculate":
            transactions = args.get("transactions", [])
            return regret_calculate(transactions, user_card_ids)

        else:
            return {"error": f"Unknown tool: {name}"}
    except (ValueError, RuntimeError) as e:
        # 幣別不支援或匯率服務暫時無法使用
        logging.warning("外幣換算失敗：%s(%s) → %s", name, args, e)
        return {"error": str(e)}
    except Exception as e:
        logging.error("Tool execution error: %s(%s) → %s", name, args, e)
        return {"error": str(e)}


def _trim_tool_result(result: dict) -> dict:
    """精簡 tool result 減少 token。只保留關鍵欄位，並標記資料來源。"""
    if "results" in result:
        trimmed_results = []
        for r in result["results"][:5]:
            trimmed_results.append({
                "bank_name": r.get("bank_name"),
                "card_name": r.get("card_name"),
                "reward_rate": r.get("reward_rate"),
                "actual_reward": r.get("actual_reward"),
                "reward_type": r.get("reward_type"),
            })
        out = {
            "merchant": result.get("merchant"),
            "amount": result.get("amount"),
            "user_owned_cards": trimmed_results,
        }
        if result.get("better_card"):
            bc = result["better_card"]
            out["better_card_not_owned"] = {
                "bank_name": bc.get("bank_name"),
                "card_name": bc.get("card_name"),
                "reward_rate": bc.get("reward_rate"),
                "actual_reward": bc.get("actual_reward"),
                "extra_reward": bc.get("extra_reward"),
            }
        # 保留外幣換算資訊，供 LLM 格式化回覆
        if result.get("fx_conversion"):
            fx = result["fx_conversion"]
            out["fx_conversion"] = {
                "display_text": fx["display_text"],   # "6000 JPY = 1264.2 TWD（匯率 0.2107）"
                "fee_text": fx["fee_text"],            # "海外手續費 1.5% = $18.96"
                "fee_amount": fx["fee_amount"],        # 供 LLM 計算淨回饋
            }
        return out
    return result


def agent_chat(
    message: str,
    history: list | None = None,
    user_card_ids: list[int] | None = None,
    max_turns: int = 5,
) -> dict:
    """
    Agent 主迴圈。
    回傳 { reply, history, tool_results }
    """
    if not _api_key():
        return {
            "reply": "系統未設定 API Key，無法使用 AI 助手功能。",
            "history": [],
            "tool_results": [],
        }

    contents = list(history) if history else []
    contents.append({"role": "user", "parts": [{"text": message}]})

    tool_results = []

    for _ in range(max_turns):
        try:
            resp_json = _call_with_retry(_gemini_request, contents)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 and history:
                # 400 可能是 history 格式問題 → 清空重試
                logging.warning("Gemini 400 with history, retrying without history")
                contents = [{"role": "user", "parts": [{"text": message}]}]
                try:
                    resp_json = _call_with_retry(_gemini_request, contents)
                except Exception:
                    return {
                        "reply": "抱歉，AI 助手暫時無法回應，請稍後再試。",
                        "history": [],
                        "tool_results": [],
                    }
            else:
                return {
                    "reply": "抱歉，AI 助手暫時無法回應，請稍後再試。",
                    "history": [],
                    "tool_results": [],
                }
        except httpx.TimeoutException:
            return {
                "reply": "抱歉，AI 回應超時了，請稍後再試。",
                "history": [],
                "tool_results": [],
            }
        except Exception as e:
            logging.error("Gemini request error: %s", e)
            return {
                "reply": "抱歉，AI 助手暫時無法回應，請稍後再試。",
                "history": [],
                "tool_results": [],
            }

        # 解析回應
        candidate = resp_json.get("candidates", [{}])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        if not parts:
            return {
                "reply": "抱歉，AI 助手暫時無法回應，請稍後再試。",
                "history": contents,
                "tool_results": tool_results,
            }

        # 將 model response 加入 contents
        contents.append({"role": "model", "parts": parts})

        # 檢查是否有 function call
        function_calls = [p for p in parts if "functionCall" in p]

        if not function_calls:
            # 取出文字回覆，結束迴圈
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            reply = "\n".join(text_parts).strip()
            if not reply:
                reply = "抱歉，我無法理解你的問題。請試試輸入消費情境，例如「星巴克 300」"
            return {
                "reply": reply,
                "history": contents,
                "tool_results": tool_results,
            }

        # 執行所有 function calls，收集 responses
        function_response_parts = []
        for fc_part in function_calls:
            fc = fc_part["functionCall"]
            fn_name = fc["name"]
            fn_args = fc.get("args", {})

            logging.info("🔧 tool call: %s(%s)", fn_name, json.dumps(fn_args, ensure_ascii=False))

            result = _execute_tool(fn_name, fn_args, user_card_ids)
            tool_results.append({
                "name": fn_name,
                "args": fn_args,
                "result": result,
            })

            trimmed = _trim_tool_result(result)
            function_response_parts.append({
                "functionResponse": {
                    "name": fn_name,
                    "response": trimmed,
                }
            })

        # 將 function responses 加入 contents
        contents.append({"role": "user", "parts": function_response_parts})

    # max_turns 耗盡
    return {
        "reply": "抱歉，處理時間過長，請稍後再試。",
        "history": contents,
        "tool_results": tool_results,
    }
