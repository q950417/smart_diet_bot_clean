# chat.py 範例
import os
import openai
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT_CHAT = "你是一個溫暖的飲食小幫手…"

def generate_reply(user_msg: str) -> str:
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_CHAT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.8,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("【Debug】generate_reply 錯誤：", repr(e))
        return "抱歉，暫時無法以文字形式回答。"

SYSTEM_PROMPT_NUTRITION = "你是一位專業的營養師助理…"

def generate_nutrition_advice(food_name, calories, protein, fat, carbs) -> str:
    user_content = (
        f"食物：{food_name}\n"
        f"熱量：{calories} kcal\n"
        f"蛋白質：{protein} g\n"
        f"脂肪：{fat} g\n"
        f"碳水：{carbs} g\n"
        "請根據以上資訊，給我一句營養師建議。"
    )
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_NUTRITION},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("【Debug】generate_nutrition_advice 錯誤：", repr(e))
        return "抱歉，暫時無法生成飲食建議。"
