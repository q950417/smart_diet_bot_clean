import os, tempfile, asyncio, json
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

# -------------------------------------------------------
# 讀 .env
# -------------------------------------------------------
load_dotenv()                        # .env 放在專案根目錄
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# -------------------------------------------------------
#  LINE v3  SDK 初始化
# -------------------------------------------------------
from linebot.v3.webhook   import WebhookParser
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.exceptions import LineBotApiError

config     = Configuration(access_token=CHANNEL_TOKEN)  # ← 這裡就能用
api_client = AsyncApiClient(configuration=config)
line_bot   = AsyncMessagingApi(api_client=api_client)
parser     = WebhookParser(CHANNEL_SECRET)

# -------------------------------------------------------
#  你自己的模組
# -------------------------------------------------------
from food_classifier import classify_and_lookup
from chat            import generate_nutrition_advice, chat_reply

# -------------------------------------------------------
#  FastAPI APP
# -------------------------------------------------------
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# -------------------------------------------------------
#  Webhook 入口
# -------------------------------------------------------
@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await asyncio.gather(*[dispatch(e) for e in events])
    return "OK"

# -------------------------------------------------------
#  事件分派
# -------------------------------------------------------
async def dispatch(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        elif event.message.type == "image":
            await handle_image(event)
    except LineBotApiError as e:
        print("[LineBotApiError]", e, flush=True)
    except Exception as e:
        print("[Unhandled]", e, flush=True)

# === 文字訊息 =================================================
async def handle_text(event):
    text = event.message.text.strip()

    # 先當作食物名稱查
    info = await classify_and_lookup(text=text)
    if info:
        reply = fmt_nutrition(info)
    else:
        # 如果不是食物，就丟到 GPT 陪聊
        reply = await chat_reply(text)

    await reply_text(event.reply_token, reply)

# === 圖片訊息 =================================================
async def handle_image(event):
    # 1) 下載圖片到暫存檔
    msg_id  = event.message.id
    content = await line_bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    # 2) 辨識 + 查營養
    info = await classify_and_lookup(img_path=tmp_path)
    reply = fmt_nutrition(info) if info else "暫時看不出這是什麼食物 QQ"

    await reply_text(event.reply_token, reply)

# === 共用小工具 ===============================================
def fmt_nutrition(info: dict) -> str:
    return (
        f"{info['name']} (預估)\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g；脂肪 {info['fat']} g；碳水 {info['carbs']} g\n"
        + generate_nutrition_advice(
            info["name"],
            info["calories"], info["protein"],
            info["fat"],      info["carbs"]
        )
    )

async def reply_text(token, text):
    await line_bot.reply_message(
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text)]
        )
    )
