import os, tempfile, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

# ── LINE v3 SDK ──────────────────────────────────────────
from linebot.webhook import WebhookParser
from linebot.exceptions import LineBotApiError
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# ── 子模組 ───────────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat import generate_chat_reply, generate_nutrition_advice

# ── LINE 初始化 ─────────────────────────────────────────
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

parser = WebhookParser(CHANNEL_SECRET)

cfg        = Configuration(access_token=CHANNEL_TOKEN)
api_client = AsyncApiClient(cfg)
line_bot   = AsyncMessagingApi(api_client)

# ── FastAPI ─────────────────────────────────────────────
app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# ── Webhook 入口 ────────────────────────────────────────
@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 並行處理
    await asyncio.gather(*[dispatch(ev) for ev in events])
    return "OK"

# ── 事件分派 ────────────────────────────────────────────
async def dispatch(ev):
    try:
        if ev.message.type == "text":
            await handle_text(ev)
        elif ev.message.type == "image":
            await handle_image(ev)
    except Exception as e:
        # 出錯最多印 log，不再嘗試第二次 reply
        print("[Unhandled]", e, flush=True)

# ── 文字訊息 ────────────────────────────────────────────
async def handle_text(ev):
    q = ev.message.text.strip()
    info = await classify_and_lookup(text=q)

    if info:
        reply = format_nutrition(info)
    else:
        reply = generate_chat_reply(q)

    await safe_reply(ev.reply_token, reply)

# ── 圖片訊息 ────────────────────────────────────────────
async def handle_image(ev):
    msg_id  = ev.message.id
    content = await line_bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        for chunk in content.iter_content():
            fp.write(chunk)
        tmp = fp.name

    info  = await classify_and_lookup(img_path=tmp)
    reply = format_nutrition(info) if info else "抱歉，我看不出這張是什麼食物 QQ"
    await safe_reply(ev.reply_token, reply)

# ── 共用工具 ────────────────────────────────────────────
def format_nutrition(d: dict) -> str:
    return (
        f"{d.get('name','?')} (預估)\n"
        f"熱量 {d.get('calories','?')} kcal\n"
        f"蛋白質 {d.get('protein','?')} g；"
        f"脂肪 {d.get('fat','?')} g；"
        f"碳水 {d.get('carbs','?')} g\n"
        + generate_nutrition_advice(
            d.get('name'), d.get('calories'),
            d.get('protein'), d.get('fat'), d.get('carbs'))
    )

async def safe_reply(token, text):
    """
    LINE 規則：一個 reply_token 只能用一次。
    這裡包 try/except，失敗只印 log，不再第二次呼叫。
    """
    try:
        await line_bot.reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=[TextMessage(text=text[:1000])]  # LINE 上限
            )
        )
    except LineBotApiError as e:
        print("[LineBotApiError]", e.status_code, e.error.details, flush=True)
