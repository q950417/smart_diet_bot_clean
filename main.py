import os, tempfile, asyncio, json
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv; load_dotenv()

# ---------- LINE v3 SDK ----------
from linebot.v3.webhook   import WebhookParser
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.exceptions import ApiException  # ← v3 只有這個例外類型

# ---------- 你的模組 ----------
from food_classifier import classify_and_lookup

# ---------- LINE 初始化 ----------
app = FastAPI()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

config     = Configuration(access_token=CHANNEL_TOKEN)
api_client = AsyncApiClient(configuration=config)
line_bot   = AsyncMessagingApi(api_client=api_client)
parser     = WebhookParser(CHANNEL_SECRET)

# ---------- healthz (Render) ----------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ---------- webhook 入口 ----------
@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 依序處理事件（不用 GPT，速度快，逐一就好）
    for ev in events:
        if ev.message.type == "text":
            await handle_text(ev)
        elif ev.message.type == "image":
            await handle_image(ev)

    return "OK"

# ---------- 文字 ----------
async def handle_text(event):
    query = event.message.text.strip()
    info  = await classify_and_lookup(text=query)

    if info:
        reply = format_nutrition(info)
    else:
        reply = "抱歉，暫時找不到這項食物的營養資料 QQ"

    await reply_text(event.reply_token, reply)

# ---------- 圖片 ----------
async def handle_image(event):
    # 下載圖片到暫存檔
    content = await line_bot.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    info = await classify_and_lookup(img_path=tmp_path)
    if info:
        reply = format_nutrition(info)
    else:
        reply = "抱歉，我看不出這是什麼食物 QQ"

    await reply_text(event.reply_token, reply)

# ---------- utils ----------
def format_nutrition(d: dict) -> str:
    return (
        f"{d['name']} (預估)\n"
        f"熱量 {d['calories']} kcal\n"
        f"蛋白質 {d['protein']} g、脂肪 {d['fat']} g、碳水 {d['carbs']} g"
    )

async def reply_text(token: str, text: str):
    try:
        await line_bot.reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=text)]
            )
        )
    except ApiException as e:
        # 例如 Invalid reply token 等，列印即可
        print("[ApiException]", e)
