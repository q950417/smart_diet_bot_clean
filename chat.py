import os
from dotenv import load_dotenv; load_dotenv()
import openai

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = (
    "你是一位溫暖、實用的營養師助手。"
    "根據提供的食物與營養資訊，給出簡潔建議（50字內），"
    "最後附一句貼心健康提醒。"
)

def generate_nutrition_advice(name, cal, pro, fat, carb) -> str:
    try:
        user_msg = f"食物：{name}\n熱量:{cal}kcal 蛋白質:{pro}g 脂肪:{fat}g 碳水:{carb}g"
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user",   "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("[Debug] generate_nutrition_advice 發生錯誤：", e, flush=True)
        return "抱歉，暫時無法生成建議。"
