# main.py  ── 完整檔案覆蓋版
import os, tempfile, asyncio, textwrap
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()                                  # 讀取 .env

# ── LINE v3 SDK ───────────────────────────────────────────
from linebot.v3.messaging             import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.messaging.exceptions  import ApiException   # ← 正確位置
from linebot.v3.webhook               import WebhookParser

# ── 自己的副程式 ──────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat            import try_greet, format_nutrition

# ── 初始化 LINE client ────────────────────────────────────
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

config      = Configuration(access_token=CHANNEL_TOKEN)
api_client  = AsyncApiClient(configuration=config)
line_bot    = AsyncMessagingApi(api_client)
parser      = WebhookParser(CHANNEL_SECRET)

# ── FastAPI ------------------------------------------------
app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ── Webhook ------------------------------------------------
@app.post("/callback")
async def callback(request: Request):
    raw_body  = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        events = parser.parse(raw_body.decode(), signature)
    except Exception as e:
        raise HTTPException(400, str(e))

    await asyncio.gather(*[handle_event(ev) for ev in events])
    return "OK"


# ── 事件分派 ----------------------------------------------
async def handle_event(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        elif event.message.type == "image":
            await handle_image(event)
    except ApiException as e:           # LINE API 例外
        print("[Line error]", e.status, e.message)
    except Exception as e:              # 其他未預期例外
        print("[Unhandled]", e)


# ── 文字訊息 ----------------------------------------------
async def handle_text(event):
    msg = event.message.text.strip()

    # (1) 招呼語固定回覆
    greet = try_greet(msg)
    if greet:
        await reply_text(event.reply_token, greet)
        return

    # (2) 視為食物名稱 → 查營養
    info = await classify_and_lookup(text=msg)
    if info:
        await reply_text(event.reply_token, format_nutrition(info))
    else:
        await reply_text(event.reply_token, "抱歉找不到這道食物的營養資訊～")


# ── 圖片訊息 ----------------------------------------------
async def handle_image(event):
    # 下載影像到暫存
    content = await line_bot.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        img_path = fp.name

    # 影像分類 + 查營養
    info = await classify_and_lookup(img_path=img_path)
    if info:
        await reply_text(event.reply_token, format_nutrition(info))
    else:
        await reply_text(event.reply_token, "這張照片我暫時認不出是什麼食物 QQ")


# ── 共用：傳送文字 ----------------------------------------
async def reply_text(token: str, text: str):
    await line_bot.reply_message(
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text)]
        )
    )
