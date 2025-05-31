# main.py

import os
import tempfile
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from linebot.v3.webhook import WebhookParser, WebhookHandler
from linebot.v3.messaging import (
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage
)

from food_classifier import classify_and_lookup
from chat import generate_reply, generate_nutrition_advice

# ➡️ 載入 .env，讓下面的 os.getenv(...) 能夠拿到所有金鑰
load_dotenv(dotenv_path=".env")

app = FastAPI()
parser   = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))
handler  = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
line_api = AsyncMessagingApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    for event in events:
        # 如果是圖片
        if isinstance(event.message, ImageMessage):
            await handle_image(event)
        # 如果是文字
        elif isinstance(event.message, TextMessage):
            await handle_text(event)
    return "OK"

async def handle_text(event):
    """
    處理使用者傳文字訊息：直接丟給 GPT-4o-mini 當陪聊，回覆結果
    """
    text = event.message.text.strip()
    reply = generate_reply(text)
    await safe_reply(event.reply_token, reply)

async def handle_image(event):
    """
    處理使用者傳圖片：
      1. 下載圖片到本地臨時檔 (tmp_path)
      2. classify_and_lookup(tmp_path) → 拿 {name, calories, protein, fat, carbs}
      3. 呼叫 generate_nutrition_advice(...) → 取得建議文字
      4. 組「食物名稱＋數值＋建議」回覆給使用者
    """
    # 1️⃣ 下載圖片
    msg_id  = event.message.id
    content = await line_api.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        async for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    # 2️⃣ 圖片分類 + 營養查詢
    result = await classify_and_lookup(tmp_path)
    if result:
        # 3️⃣ 拆出四項數值
        food_name = result["name"]
        calories  = result["calories"]
        protein   = result["protein"]
        fat       = result["fat"]
        carbs     = result["carbs"]

        # 4️⃣ 呼叫 GPT 生成營養建議
        advice_text = generate_nutrition_advice(
            food_name, calories, protein, fat, carbs
        )

        # 5️⃣ 組成最終回覆
        reply = (
            f"辨識到：「{food_name}」\n"
            f"卡路里：{calories} kcal\n"
            f"蛋白質：{protein} g\n"
            f"脂肪：{fat} g\n"
            f"碳水：{carbs} g\n"
            f"建議：{advice_text}"
        )
    else:
        reply = "抱歉，無法辨識或查詢這張圖片的營養資料，請改用文字輸入或提供更清晰的照片。"

    # 安全地回覆給使用者
    await safe_reply(event.reply_token, reply)

async def safe_reply(token: str, message: str):
    """
    用 try/except 包裹 LINE 回覆，避免失敗時程式炸掉
    """
    try:
        await line_api.reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=message)]
            )
        )
    except Exception as e:
        print("【Debug】LINE 回覆錯誤：", repr(e))

@app.get("/healthz")
def health_check():
    return {"status": "ok"}
