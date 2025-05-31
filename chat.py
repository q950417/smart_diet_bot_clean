import os, openai
from dotenv import load_dotenv
load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 系統提示：飲食建議
SYS_NUTRITION = (
    "你是一位溫暖、實用的營養師助手。"
    "根據提供的食物與營養資訊，用 50 字內給出建議，最後附一句貼心提醒。"
)

# 系統提示：一般陪聊
SYS_CHAT = (
    "你是一位親切、幽默的聊天夥伴。回答要簡短、有溫度，並在句尾附一句飲食/健康小提醒。"
)

# ── 1) 產生營養建議 ───────────────────────────────────
def generate_nutrition_advice(name, cal, pro, fat, carb) -> str:
    try:
        user = f"食物：{name}\n熱量:{cal}kcal 蛋白質:{pro}g 脂肪:{fat}g 碳水:{carb}g"
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYS_NUTRITION},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("[Debug] nutrition_advice 失敗:", e, flush=True)
        return "抱歉，暫時無法生成飲食建議。"

# ── 2) 一般陪聊 ───────────────────────────────────────
def generate_chat_reply(user_msg: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYS_CHAT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.8,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("[Debug] chat_reply 失敗:", e, flush=True)
        return "抱歉，目前無法回覆，請稍後再試～"
