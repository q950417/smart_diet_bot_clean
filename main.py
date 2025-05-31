import os, tempfile, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

# ── LINE v3 SDK ──────────────────────────────────────────
from linebot.webhook import WebhookParser
from linebot.exceptions import LineBotApiError

from linebot.v3.messaging import (
    AsyncMessagingApi, ReplyMessageRequest,
    TextMessage, ImageMessage
)
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging.api_client import AsyncApiClient

# ── 子模組 ───────────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat import (
    generate_nutrition_advice,
    generate_chat_reply,
)

# ── 初始化 LINE 物件 ─────────────────────────────────────
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

parser = WebhookParser(CHANNEL_SECRET)

config = Configuration(access_token=CHANNEL_TOKEN)
async_cli = AsyncApiClient(configuration=config)
line_bot  = AsyncMessagingApi(async_cli)

# ── FastAPI 物件 ─────────────────────────────────────────
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ── Webhook 入口 ────────────────────────────────────────
@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    print("[RAW]", body[:120], flush=True)

    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
        print("[Debug] 事件數 =", len(events), flush=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await asyncio.gather(*[dispatch(e) for e in events])
    return "OK"

# ── 事件分派 ─────────────────────────────────────────────
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

# ── 文字訊息 ────────────────────────────────────────────
async def handle_text(event):
    query = event.message.text.strip()
    info  = await classify_and_lookup(text=query)

    if info:
        reply = format_nutrition(info)
    else:
        reply = generate_chat_reply(query)          # 陪聊
    await reply_text(event.reply_token, reply)

# ── 圖片訊息 ────────────────────────────────────────────
async def handle_image(event):
    msg_id  = event.message.id
    content = await line_bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    info = await classify_and_lookup(img_path=tmp_path)
    reply = format_nutrition(info) if info else "抱歉，看不出這是什麼食物 QQ"
    await reply_text(event.reply_token, reply)

# ── 小工具 ──────────────────────────────────────────────
def format_nutrition(info: dict) -> str:
    return (
        f"{info.get('name','?')} (預估)\n"
        f"熱量 {info.get('calories','?')} kcal\n"
        f"蛋白質 {info.get('protein','?')} g；"
        f"脂肪 {info.get('fat','?')} g；"
        f"碳水 {info.get('carbs','?')} g\n"
        + generate_nutrition_advice(
            info.get('name'), info.get('calories'),
            info.get('protein'), info.get('fat'), info.get('carbs'))
    )

async def reply_text(token, text):
    try:
        await line_bot.reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=text)]
            )
        )
        print("[Debug] 已呼叫 reply_message", flush=True)
    except LineBotApiError as e:
        print("[LineBotApiError]", e.status_code, e.error.details, flush=True)
    except Exception as e:
        print("[Unhandled Exception]", e, flush=True)
