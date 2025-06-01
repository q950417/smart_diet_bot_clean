import os, json, tempfile, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

# ─── LINE v3 SDK ─────────────────────────────────────────
from linebot.v3.webhook     import WebhookParser
from linebot.v3.messaging   import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.exceptions  import LineBotSdkException

# ─── 你的功能模組 ────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat            import nutrition_only_reply        # 不打 GPT

# ─── 初始化 ──────────────────────────────────────────────
app = FastAPI()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

_config     = Configuration(access_token=CHANNEL_TOKEN)
_client     = AsyncApiClient(configuration=_config)
line_bot    = AsyncMessagingApi(api_client=_client)
parser      = WebhookParser(CHANNEL_SECRET)


# Health Check 給 Render
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ─── Webhook 入口 ───────────────────────────────────────
@app.post("/callback")
async def callback(request: Request):
    body_raw = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body_raw.decode(), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 事件併發處理
    await asyncio.gather(*[handle_event(ev) for ev in events])
    return "OK"


async def handle_event(event):
    try:
        m = event.message
        if m.type == "text":
            await handle_text(event, m.text.strip())
        elif m.type == "image":
            await handle_image(event, m.id)
    except LineBotSdkException as e:
        print("[LineBotSdkException]", e, flush=True)
    except Exception as e:
        print("[Unhandled]", e, flush=True)


# ─── 文字：食物名稱 ──────────────────────────────────────
async def handle_text(event, text: str):
    info = classify_and_lookup(text=text)   # 只查文字
    reply = nutrition_only_reply(info, text)
    await line_bot.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply)]
        )
    )


# ─── 圖片：先存檔再辨識 ───────────────────────────────────
async def handle_image(event, msg_id: str):
    content = await line_bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp_path = fp.name

    info  = await classify_and_lookup(img_path=tmp_path)
    reply = nutrition_only_reply(info, "這張照片")
    await line_bot.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply)]
        )
    )
