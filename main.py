import os, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

# ─── 讀 .env ─────────────────────────────────────────────
load_dotenv()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# ─── LINE v3 SDK 初始化（完全不 import 例外類別） ─────────
from linebot.v3.webhook   import WebhookParser
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)

cfg         = Configuration(access_token=CHANNEL_TOKEN)
api_client  = AsyncApiClient(configuration=cfg)
line_bot    = AsyncMessagingApi(api_client=api_client)
parser      = WebhookParser(CHANNEL_SECRET)

# ─── 你的子模組 ──────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat            import generate_nutrition_advice, chat_reply

# ─── FastAPI APP ────────────────────────────────────────
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ─── Webhook 入口 ───────────────────────────────────────
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

# ─── 事件分派 ───────────────────────────────────────────
async def dispatch(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        else:
            await reply_text(event.reply_token, "目前只支援文字訊息，圖片之後再來！")
    except Exception as e:          # ← 不分 SDK 版本，直接抓
        print("[Unhandled]", e, flush=True)

# === 文字訊息 =================================================
async def handle_text(event):
    text = event.message.text.strip()

    info = await classify_and_lookup(text=text)   # 試著查營養
    if info:
        reply = fmt_nutrition(info)
    else:
        try:
            reply = await chat_reply(text)        # GPT 陪聊
        except Exception as e:
            print("[OpenAIError]", e, flush=True)
            reply = "目前額度不足，稍後再試～"

    await reply_text(event.reply_token, reply)

# === 共用工具 =================================================
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
            messages=[TextMessage(text=text[:1000])]   # LINE 最長 1000 chars
        )
    )
