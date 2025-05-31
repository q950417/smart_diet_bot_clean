"""
聊天 & 飲食建議模組
-------------------------------------------------
當 OpenAI 額度不足 (429) 就回到簡易 fallback 文案，
不再拋例外，主程式才不會重複 reply。
"""

import os, openai, asyncio
from typing import Optional, Union

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# OpenAI 新版 v1.x 介面
async def _chat(system: str, user: str) -> str:
    resp = await openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",    "content": user},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ── 使用者單純聊天 ─────────────────────────────────────
def generate_chat_reply(query: str) -> str:
    try:
        return asyncio.run(
            _chat(
                "你是一個友善的營養聊天機器人，簡短回答。",
                query,
            )
        )
    except Exception as e:
        # 429 / 401 / 其他錯誤都回 fallback，不再往外丟
        print("[Debug] chat_reply 失敗:", e, flush=True)
        return "抱歉，暫時無法回覆，請稍後再試～"


# ── 依營養數值給建議 ───────────────────────────────────
def generate_nutrition_advice(
    name: str,
    kcal: Union[int, float, None],
    protein: Union[int, float, None],
    fat: Union[int, float, None],
    carb: Union[int, float, None],
) -> str:
    try:
        prompt = (
            f"以下是 {name or '食物'} 的營養資料："
            f"熱量 {kcal} kcal、蛋白質 {protein} g、脂肪 {fat} g、碳水 {carb} g。\n"
            "用繁體中文給出 1 句 40 字內的飲食建議，不要重複提供數字。"
        )
        return asyncio.run(
            _chat(
                "你是專業營養師，回答保持簡短。",
                prompt,
            )
        )
    except Exception as e:
        print("[Debug] nutrition_advice 失敗:", e, flush=True)
        return "抱歉，暫時無法生成飲食建議。"
