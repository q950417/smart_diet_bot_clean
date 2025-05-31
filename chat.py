# === chat.py  =========================================================
"""
集中處理：
1. OpenAI GPT 陪聊 (async chat_reply)
2. 根據營養數值產生飲食建議 (generate_nutrition_advice)
-----------------------------------------------------------------------
openai-python 已升到 1.x；用 AsyncOpenAI() 新介面。
"""

import os
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError

load_dotenv()
_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------- OpenAI 非同步用戶端 ----------
client = AsyncOpenAI(api_key=_OPENAI_KEY) if _OPENAI_KEY else None

_SYSTEM_PROMPT = (
    "你是一個溫暖的飲食小幫手，回答時先簡短回應使用者，"
    "再補一句貼心的飲食提醒。"
)

# ------------------------------------------------------------------ #
#  async chat_reply : str -> str
# ------------------------------------------------------------------ #
async def chat_reply(user_msg: str) -> str:
    """
    ❶ 有金鑰 → 呼叫 GPT ❷ 沒金鑰 / 失敗 → 回預設訊息
    """
    if not client:
        return "抱歉，尚未設定 OpenAI API 金鑰，無法回覆～"

    try:
        rsp = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            timeout=10,          # 秒
        )
        return rsp.choices[0].message.content.strip()

    # OpenAI 相關錯誤 → 印 log，回預設句
    except OpenAIError as e:
        print("[OpenAIError]", e, flush=True)
    except Exception as e:
        print("[chat_reply-unexpected]", e, flush=True)

    return "抱歉，暫時無法回覆，請稍後再試～"

# ------------------------------------------------------------------ #
#  generate_nutrition_advice : (name, kcal, pro, fat, carb) -> str
# ------------------------------------------------------------------ #
def generate_nutrition_advice(
    food_name: str,
    calories: float | None,
    protein:  float | None,
    fat:      float | None,
    carbs:    float | None,
) -> str:
    """
    有完整營養數值就回個人化建議；缺任何一項就回泛用提醒。
    """
    if None in (calories, protein, fat, carbs):
        return "記得均衡飲食、多蔬果、足量蛋白質並保持水分喔！"

    return (
        f"吃了 {food_name} 後，今日建議熱量控制在 ~{calories+300:.0f} kcal 內，"
        f"並把蛋白質拉到 {protein+15:.1f} g 以上；"
        f"接下來少油少糖、多蔬菜與適量運動，就能維持身體輕盈唷！"
    )
# ====================================================================
