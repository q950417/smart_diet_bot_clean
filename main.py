# ─── main.py ────────────────────────────────────────────
import os, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()          # 讀取 .env

# ─── LINE v3 SDK（**同步版即可**） ─────────────────────
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    MessagingApi, ReplyMessageRequest, TextMessage
)
from linebot.v3.exceptions import LineBotApiError

# ─── 內部模組 ──────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat import (
    generate_chat_reply,
    generate_nutrition_advice,
)

# ─── FastAPI 初始化 ───────────────────────────────────
app = FastAPI()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
parser   = WebhookParser(CHANNEL_SECRET)
line_bot = MessagingApi(CHANNEL_TOKEN)

# ─── 健康檢查 (Render) ────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ─── Webhook 入口 ─────────────────────────────────────
@app.post("/callback")
async def callback(request: Request):
    body      = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 逐一處理（簡化：逐個 await，已足夠）
    for ev in events:
        await handle_event(ev)

    return "OK"

# ─── 事件分發 ─────────────────────────────────────────
async def handle_event(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        else:
            await reply_text(event.reply_token, "抱歉，目前僅支援文字查詢。")
    except LineBotApiError as e:
        print("[LineBotApiError]", e, flush=True)
    except Exception as e:
        print("[Unhandled]", e, flush=True)

# ─── 文字訊息處理 ─────────────────────────────────────
async def handle_text(event):
    q = event.message.text.strip()

    # 1) 嘗試直接查食物
    info = await classify_and_lookup(text=q)
    if info:
        reply = format_nutrition(info)
    else:
        # 2) 當成閒聊
        reply = generate_chat_reply(q)

    await reply_text(event.reply_token, reply)

# ─── 共用工具 ─────────────────────────────────────────
def format_nutrition(info: dict) -> str:
    return (
        f"{info['name']} (預估)\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g；脂肪 {info['fat']} g；碳水 {info['carbs']} g\n"
        + generate_nutrition_advice(
            info['name'], info['calories'],
            info['protein'], info['fat'], info['carbs']
        )
    )

async def reply_text(token: str, text: str):
    # MessagingApi 是同步函式 → 用執行緒避免卡主 event loop
    await asyncio.to_thread(
        line_bot.reply_message,
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text)]
        )
    )
