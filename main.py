import os, asyncio, tempfile, httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv; load_dotenv()

# ---------- LINE v3 ----------
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import LineBotApiError

from food_classifier import classify_and_lookup

# ---------- 初始 ----------
app = FastAPI()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
config   = Configuration(access_token=CHANNEL_TOKEN)
bot      = AsyncMessagingApi(AsyncApiClient(config))
parser   = WebhookParser(CHANNEL_SECRET)

# ---------- 固定陪聊觸發 ----------
TRIGGERS = {
    "哈囉": "嗨！請傳食物名稱或照片來查營養～",
    "hi":   "Hello! Send me food name or image 😊",
}

# ---------- 建議 ----------
def advice(kcal: float) -> str:
    if kcal <= 100:  return "熱量很低，放心享用！"
    if kcal <= 300:  return "熱量適中，注意均衡飲食。"
    if kcal <= 600:  return "熱量偏高，建議配點蔬菜或多運動。"
    return "熱量很高，請適量即可喔！"

def format_info(info: dict) -> str:
    return (
        f"{info['name']} (100 g)\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g｜脂肪 {info['fat']} g｜碳水 {info['carbs']} g\n"
        f"👉 {advice(info['calories'])}"
    )

# ---------- healthz ----------
@app.get("/healthz")
async def _h(): return {"ok": True}

# ---------- webhook ----------
@app.post("/callback")
async def callback(req: Request):
    body = await req.body(); sig = req.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await asyncio.gather(*[handle_event(e) for e in events])
    return "OK"

async def handle_event(event):
    try:
        m = event.message
        if m.type == "text":
            await on_text(event, m.text.strip())
        elif m.type == "image":
            await on_image(event, m.id)
    except LineBotApiError as e:
        print("[Line error]", e, flush=True)

# ---------- handlers ----------
async def on_text(event, txt: str):
    if txt in TRIGGERS:                 # ▶️ 固定陪聊
        await reply(event, TRIGGERS[txt]); return

    info = await classify_and_lookup(text=txt)
    if info:
        await reply(event, format_info(info))
    else:
        await reply(event, "抱歉，找不到這項食物的營養資料 QQ")

async def on_image(event, msg_id: str):
    # 下載圖片到暫存
    resp = await bot.get_message_content(msg_id)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        async for chunk in resp.iter_content():
            fp.write(chunk)
        path = fp.name

    info = await classify_and_lookup(img_path=path)
    if info:
        await reply(event, format_info(info))
    else:
        await reply(event, "抱歉，這張圖片我看不出是什麼食物 QQ")

async def reply(event, text: str):
    await bot.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[TextMessage(text=text)]
    ))
