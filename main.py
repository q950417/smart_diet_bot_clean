import os, tempfile, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv; load_dotenv()

# ---------- LINE v3 ----------
from linebot.v3.webhook   import WebhookParser
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
# ★ 不再 import ApiException，直接用通用 Exception ★

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

# ---------- healthz ----------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ---------- webhook ----------
@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    for ev in events:
        if ev.message.type == "text":
            await handle_text(ev)
        elif ev.message.type == "image":
            await handle_image(ev)
    return "OK"

# ---------- handlers ----------
async def handle_text(event):
    query = event.message.text.strip()
    info  = await classify_and_lookup(text=query)
    reply = format_nutrition(info) if info else "抱歉，找不到這項食物的營養資料 QQ"
    await reply_text(event.reply_token, reply)

async def handle_image(event):
    content = await line_bot.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        img_path = fp.name

    info  = await classify_and_lookup(img_path=img_path)
    reply = format_nutrition(info) if info else "抱歉，我看不出這是什麼食物 QQ"
    await reply_text(event.reply_token, reply)

# ---------- utils ----------
def format_nutrition(d: dict | None) -> str:
    if not d:
        return ""
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
    except Exception as e:
        # 任何 LINE API 例外直接列印並忽略（避免整個 webhook 崩潰）
        print("[LINE Exception]", e)
