import os, tempfile, asyncio, json
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()                              # 讀取 .env

# ─── LINE v3 SDK ─────────────────────────────────────────
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncMessagingApi, ReplyMessageRequest,
    TextMessage, ImageMessage
)
from linebot.v3.exceptions import LineBotApiError
# ─── 你的子模組 ──────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat import generate_nutrition_advice

# ─── 初始化 ──────────────────────────────────────────────
app = FastAPI()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
parser   = WebhookParser(CHANNEL_SECRET)
line_bot = AsyncMessagingApi(CHANNEL_TOKEN)

# ─── Health check (Render) ──────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ─── Webhook 入口 ───────────────────────────────────────
@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    print("[RAW] ", body[:120], flush=True)
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Debug：印事件，看得到就代表 LINE → Render 正常
    print(f"[Debug] 事件數：{len(events)}", flush=True)

    # 並行處理所有事件
    await asyncio.gather(*[dispatch(event) for event in events])
    return "OK"

# ─── 依事件類型呼叫處理函式 ──────────────────────────────
async def dispatch(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        elif event.message.type == "image":
            await handle_image(event)
    except LineBotApiError as e:
        print("[LineBotApiError]", e, flush=True)
    except Exception as e:
        print("[Unhandled Exception]", e, flush=True)

# ─── 文字訊息 ────────────────────────────────────────────
async def handle_text(event):
    query = event.message.text.strip()
    info  = await classify_and_lookup(text=query)  # 文字直接查
    if info:
        reply = format_nutrition(info)
    else:
        reply = generate_nutrition_advice(query, None, None, None, None)
    await reply_text(event.reply_token, reply)

# ─── 圖片訊息 ────────────────────────────────────────────
async def handle_image(event):
    # 1. 下載圖片到暫存檔
    msg_id  = event.message.id
    content = await line_bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    # 2. 辨識 + 查營養
    info = await classify_and_lookup(img_path=tmp_path)
    if info:
        reply = format_nutrition(info)
    else:
        reply = "抱歉，這張圖片我暫時看不太出來是什麼食物 QQ"

    await reply_text(event.reply_token, reply)

# ─── 共用小工具 ──────────────────────────────────────────
def format_nutrition(info: dict) -> str:
    return (
        f"{info['name']} (預估)\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g；脂肪 {info['fat']} g；碳水 {info['carbs']} g\n"
        + generate_nutrition_advice(
            info['name'], info['calories'],
            info['protein'], info['fat'], info['carbs'])
    )

async def reply_text(token, text):
    await line_bot.reply_message(
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text)]
        )
    )
