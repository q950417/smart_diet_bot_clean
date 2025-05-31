# === main.py  ============================================
import os, tempfile, asyncio, json
from fastapi import FastAPI, Request, HTTPException

from dotenv import load_dotenv
load_dotenv()                                       # 讀 .env

# ---------- LINE v3 SDK ----------
from linebot.v3.webhook     import WebhookParser
from linebot.v3.messaging   import (
    MessagingApi, ReplyMessageRequest, TextMessage
)
# ↓ 下載圖片還需要 AsyncMessagingApi，預留但先不用
# from linebot.v3.messaging   import AsyncMessagingApi

# ---------- 你自己的模組 ----------
from food_classifier import classify_and_lookup
from chat            import generate_nutrition_advice, chat_reply

# ---------- FastAPI ----------
app = FastAPI()

parser   = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
line_bot = MessagingApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))

# -------- health check ---------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# -------- webhook 入口 ---------
@app.post("/callback")
async def callback(request: Request):
    body = await request.body()               # bytes
    signature = request.headers.get("X-Line-Signature", "")

    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 逐一（並行）處理
    await asyncio.gather(*(dispatch(e) for e in events))
    return "OK"

# -------- 事件分派 ----------
async def dispatch(event):
    try:
        t = event.message.type
        if t == "text":
            await handle_text(event)
        elif t == "image":
            await reply_text(event.reply_token, "圖片辨識先暫停，稍後再試～")
    except Exception as e:
        # 所有未預期錯誤都寫 log，但仍嘗試回覆
        print("[Unhandled]", repr(e), flush=True)
        try:
            await reply_text(event.reply_token, "抱歉，暫時無法回覆，請稍後再試～")
        except Exception:
            pass

# -------- 文字 ----------
async def handle_text(event):
    q = event.message.text.strip()

    # 1. 先嘗試把文字當「食物名稱」查營養
    info = await classify_and_lookup(text=q)
    if info:
        txt = format_nutrition(info)
        await reply_text(event.reply_token, txt)
        return

    # 2. 查不到就丟給 GPT 陪聊
    txt = await chat_reply(q)
    await reply_text(event.reply_token, txt)

# -------- 共用 ----------
def format_nutrition(info: dict) -> str:
    return (
        f"{info['name']} (預估)\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g；脂肪 {info['fat']} g；碳水 {info['carbs']} g\n"
        f"{generate_nutrition_advice(info['name'], info['calories'], info['protein'], info['fat'], info['carbs'])}"
    )

async def reply_text(token: str, text: str):
    # MessagingApi 是同步函式 → 丟到 thread 避免阻塞
    await asyncio.to_thread(
        line_bot.reply_message,
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text[:1000])]   # LINE 限長度
        )
    )
# =========================================================
