# ─── chat.py ─────────────────────────────────────────────
"""
只要呼叫
    generate_chat_reply("嗨")
    generate_nutrition_advice(name, kcal, protein, fat, carb)
就會回傳一段文字。
遇到額度不足 / 429 等錯誤，會回 fallback 字串。
"""
import os, openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY", "")

# 想改預設回覆，直接改這兩行
FALLBACK_CHAT = "抱歉，聊天功能暫時休息中，下次再跟我說話吧！"
FALLBACK_DIET = "抱歉，暫時無法生成飲食建議～"

MODEL_ID = "gpt-3.5-turbo"          # 免費額度帳號建議用 3.5

# -------- 主要對外函式 ---------------------------------
def generate_chat_reply(query: str) -> str:
    """一般聊天"""
    try:
        return _sync_chat(
            system="你是一個友善的飲食小幫手，回答保持 30 字內。",
            user=query,
        )
    except Exception as e:
        print("[Debug] chat_reply 失敗:", e, flush=True)
        return FALLBACK_CHAT


def generate_nutrition_advice(name, kcal, protein, fat, carb) -> str:
    """帶營養數值，請 GPT 給一句建議；任何值傳 None 代表缺資料"""
    try:
        prompt = (
            f"以下是 {name or '這道食物'} 的營養資料："
            f"熱量 {kcal} kcal，蛋白質 {protein} g，脂肪 {fat} g，碳水 {carb} g。\n"
            "用繁體中文給出一句 40 字以內的健康飲食建議，不要重複數字。"
        )
        return _sync_chat(
            system="你是專業營養師，回答簡短有同理心。",
            user=prompt,
        )
    except Exception as e:
        print("[Debug] nutrition_advice 失敗:", e, flush=True)
        return FALLBACK_DIET


# -------- 內部小工具 -----------------------------------
def _sync_chat(system: str, user: str) -> str:
    """使用 OpenAI Python v1.x 同步介面；不需要 asyncio.run()"""
    resp = openai.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=120,
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()
