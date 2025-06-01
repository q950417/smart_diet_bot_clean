import os, asyncio, tempfile
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

# LINE v3
from linebot.v3.messaging             import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.messaging.exceptions  import ApiException
from linebot.v3.webhook               import WebhookParser

# 自家功能
from food_classifier import classify_and_lookup
from chat            import try_greet, format_nutrition

# LINE init
parser        = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
conf          = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
api_client    = AsyncApiClient(configuration=conf)
line_bot      = AsyncMessagingApi(api_client)

app = FastAPI()

@app.get("/healthz")
async def healthz(): return {"ok": True}

@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(400, str(e))
    await asyncio.gather(*[handle(ev) for ev in events])
    return "OK"

# ── 事件處理 ──────────────────────────────────────────────
async def handle(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        elif event.message.type == "image":
            await handle_image(event)
    except ApiException as e:
        print("[LINE-API]", e.status, e.message)

async def handle_text(event):
    msg = event.message.text.strip()
    if (g := try_greet(msg)):
        await reply_text(event.reply_token, g)
        return
    info = await classify_and_lookup(text=msg)
    await reply_text(event.reply_token,
                     format_nutrition(info) if info else "找不到營養資料 QQ")

async def handle_image(event):
    content = await line_bot.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        path = fp.name
    info = await classify_and_lookup(img_path=path)
    await reply_text(event.reply_token,
                     format_nutrition(info) if info else "這張圖認不出是什麼食物 QQ")

async def reply_text(token, text):
    await line_bot.reply_message(
        ReplyMessageRequest(reply_token=token,
                            messages=[TextMessage(text=text)])
    )
