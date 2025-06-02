import os, asyncio, tempfile, httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv ; load_dotenv()

# ── LINE SDK ───────────────────────────────────────────────────────────────────
from linebot.v3.messaging import (
    Configuration, AsyncApiClient, AsyncMessagingApi,
    ReplyMessageRequest, TextMessage,
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.webhook import WebhookParser

# ── 你自己的模組 ─────────────────────────────────────────────────────────────
from food_classifier import classify_and_lookup
from chat            import try_greet, format_nutrition

# ── LINE 初始化 ──────────────────────────────────────────────────────────────
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
conf   = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
api    = AsyncMessagingApi(AsyncApiClient(configuration=conf))

# ── FastAPI ──────────────────────────────────────────────────────────────────
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/callback")
async def callback(req: Request):
    body      = await req.body()
    signature = req.headers.get("X-Line-Signature", "")
    try:
        events = parser.parse(body.decode(), signature)
    except Exception as e:
        raise HTTPException(400, str(e))

    # 同步處理所有事件
    await asyncio.gather(*[handle(e) for e in events])
    return "OK"

# ── 事件分派 ────────────────────────────────────────────────────────────────
async def handle(event):
    try:
        if event.message.type == "text":
            await handle_text(event)
        elif event.message.type == "image":
            await handle_image(event)
    except ApiException as e:
        # 只簡單印出 LINE 平台回傳的錯誤
        print("[LINE-API]", e.status, e.body)

# ─────────────────────────────────────────────────────────────────────────────
async def handle_text(event):
    msg = event.message.text.strip()

    # 1) 先看是不是打招呼
    greet = try_greet(msg)
    if greet:
        await reply_text(event.reply_token, greet)
        return

    # 2) 查文字 → 營養
    info = await classify_and_lookup(text=msg)
    reply = format_nutrition(info) if info else "找不到營養資料 QQ"
    await reply_text(event.reply_token, reply)


async def handle_image(event):
    # 1) 從 LINE 下載原圖
    url = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
    headers = {"Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"}

    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.get(url, headers=headers)
    if resp.status_code != 200:
        await reply_text(event.reply_token, "圖片下載失敗 QQ")
        return

    # 2) 存檔、辨識、查營養
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        fp.write(resp.content)
        img_path = fp.name

    info = await classify_and_lookup(img_path=img_path)
    reply = format_nutrition(info) if info else "這張圖認不出是什麼食物 QQ"
    await reply_text(event.reply_token, reply)


# ─────────────────────────────────────────────────────────────────────────────
async def reply_text(token: str, text: str):
    await api.reply_message(
        ReplyMessageRequest(
            reply_token=token,
            messages=[TextMessage(text=text)]
        )
    )

#===================================================
# # main.py
# import os, asyncio, tempfile, httpx
# from fastapi import FastAPI, Request, HTTPException
# from dotenv import load_dotenv; load_dotenv()

# from linebot.v3.messaging             import (
#     Configuration, AsyncApiClient, AsyncMessagingApi,
#     ReplyMessageRequest, TextMessage
# )
# from linebot.v3.messaging.exceptions  import ApiException
# from linebot.v3.webhook               import WebhookParser

# from food_classifier import classify_and_lookup
# from chat            import try_reply, format_nutrition   # ← 這裡

# # ── LINE init ───────────────────────────────────────────
# parser        = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
# conf          = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
# api_client    = AsyncApiClient(configuration=conf)
# line_bot      = AsyncMessagingApi(api_client)

# app = FastAPI()

# @app.get("/healthz")
# async def healthz(): return {"ok": True}

# @app.post("/callback")
# async def callback(request: Request):
#     body      = await request.body()
#     signature = request.headers.get("X-Line-Signature", "")
#     try:
#         events = parser.parse(body.decode(), signature)
#     except Exception as e:
#         raise HTTPException(400, str(e))
#     await asyncio.gather(*[handle(ev) for ev in events])
#     return "OK"

# # ── 事件處理 ──────────────────────────────────────────────
# async def handle(event):
#     try:
#         if event.message.type == "text":
#             await handle_text(event)
#         elif event.message.type == "image":
#             await handle_image(event)
#         else:
#             # 其他訊息類型（貼圖、位置…）先忽略
#             pass
#     except ApiException as e:
#         # e.status, e.body 皆可參考
#         print("[LINE-API]", e.status, e.body)

# async def handle_text(event):
#     msg = event.message.text.strip()
#     if (g := try_reply(msg)):                     # ← 這裡
#         await reply_text(event.reply_token, g)
#         return

#     info = await classify_and_lookup(text=msg)
#     await reply_text(
#         event.reply_token,
#         format_nutrition(info) if info else "找不到營養資料 QQ"
#     )

# async def handle_image(event):
#     # 1) 透過 LINE 內容 API 下載原圖
#     url     = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
#     headers = {"Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"}
#     async with httpx.AsyncClient(timeout=30) as client:
#         r = await client.get(url, headers=headers)
#     if r.status_code != 200:
#         await reply_text(event.reply_token, "圖片下載失敗 QQ")
#         return

#     # 2) 存到暫存檔後進行辨識
#     with tempfile.NamedTemporaryFile(delete=False) as fp:
#         fp.write(r.content)
#         img_path = fp.name

#     info = await classify_and_lookup(img_path=img_path)
#     await reply_text(
#         event.reply_token,
#         format_nutrition(info) if info else "這張圖認不出是什麼食物 QQ"
#     )

# async def reply_text(token, text):
#     await line_bot.reply_message(
#         ReplyMessageRequest(
#             reply_token=token,
#             messages=[TextMessage(text=text)]
#         )
#     )



#=======================================================
# import os, asyncio, tempfile, httpx
# from fastapi import FastAPI, Request, HTTPException
# from dotenv import load_dotenv; load_dotenv()

# from linebot.v3.messaging             import (
#     Configuration, AsyncApiClient, AsyncMessagingApi,
#     ReplyMessageRequest, TextMessage
# )
# from linebot.v3.messaging.exceptions  import ApiException
# from linebot.v3.webhook               import WebhookParser

# from food_classifier import classify_and_lookup
# from chat            import try_greet, format_nutrition

# # ── LINE init ───────────────────────────────────────────
# parser        = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
# conf          = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
# api_client    = AsyncApiClient(configuration=conf)
# line_bot      = AsyncMessagingApi(api_client)

# app = FastAPI()

# @app.get("/healthz")
# async def healthz(): return {"ok": True}

# @app.post("/callback")
# async def callback(request: Request):
#     body      = await request.body()
#     signature = request.headers.get("X-Line-Signature", "")
#     try:
#         events = parser.parse(body.decode(), signature)
#     except Exception as e:
#         raise HTTPException(400, str(e))
#     await asyncio.gather(*[handle(ev) for ev in events])
#     return "OK"

# # ── 事件處理 ──────────────────────────────────────────────
# async def handle(event):
#     try:
#         if event.message.type == "text":
#             await handle_text(event)
#         elif event.message.type == "image":
#             await handle_image(event)
#     except ApiException as e:
#         # e.status, e.reason, e.body 可參考
#         print("[LINE-API]", e.status, e.body)

# async def handle_text(event):
#     msg = event.message.text.strip()
#     if (g := try_greet(msg)):
#         await reply_text(event.reply_token, g); return
#     info = await classify_and_lookup(text=msg)
#     await reply_text(event.reply_token,
#                      format_nutrition(info) if info else "找不到營養資料 QQ")

# async def handle_image(event):
#     # 1) 直接用 HTTP 抓原圖
#     url     = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
#     headers = {"Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"}
#     async with httpx.AsyncClient(timeout=30) as client:
#         r = await client.get(url, headers=headers)
#     if r.status_code != 200:
#         await reply_text(event.reply_token, "圖片下載失敗 QQ"); return

#     # 2) 存檔後辨識
#     with tempfile.NamedTemporaryFile(delete=False) as fp:
#         fp.write(r.content); img_path = fp.name
#     info = await classify_and_lookup(img_path=img_path)
#     await reply_text(event.reply_token,
#                      format_nutrition(info) if info else "這張圖認不出是什麼食物 QQ")

# async def reply_text(token, text):
#     await line_bot.reply_message(
#         ReplyMessageRequest(reply_token=token,
#                             messages=[TextMessage(text=text)])
#     )
#============================================================================

# import os, asyncio, tempfile
# from fastapi import FastAPI, Request, HTTPException
# from dotenv import load_dotenv
# load_dotenv()

# # LINE v3
# from linebot.v3.messaging             import (
#     Configuration, AsyncApiClient, AsyncMessagingApi,
#     ReplyMessageRequest, TextMessage
# )
# from linebot.v3.messaging.exceptions  import ApiException
# from linebot.v3.webhook               import WebhookParser

# # 自家功能
# from food_classifier import classify_and_lookup
# from chat            import try_greet, format_nutrition

# # LINE init
# parser        = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
# conf          = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
# api_client    = AsyncApiClient(configuration=conf)
# line_bot      = AsyncMessagingApi(api_client)

# app = FastAPI()

# @app.get("/healthz")
# async def healthz(): return {"ok": True}

# @app.post("/callback")
# async def callback(request: Request):
#     body      = await request.body()
#     signature = request.headers.get("X-Line-Signature", "")
#     try:
#         events = parser.parse(body.decode(), signature)
#     except Exception as e:
#         raise HTTPException(400, str(e))
#     await asyncio.gather(*[handle(ev) for ev in events])
#     return "OK"

# # ── 事件處理 ──────────────────────────────────────────────
# async def handle(event):
#     try:
#         if event.message.type == "text":
#             await handle_text(event)
#         elif event.message.type == "image":
#             await handle_image(event)
#     except ApiException as e:
#         print("[LINE-API]", e.status, e.message)

# async def handle_text(event):
#     msg = event.message.text.strip()
#     if (g := try_greet(msg)):
#         await reply_text(event.reply_token, g)
#         return
#     info = await classify_and_lookup(text=msg)
#     await reply_text(event.reply_token,
#                      format_nutrition(info) if info else "找不到營養資料 QQ")

# async def handle_image(event):
#     content = await line_bot.get_message_content(event.message.id)
#     with tempfile.NamedTemporaryFile(delete=False) as fp:
#         for chunk in content.iter_content():
#             fp.write(chunk)
#         path = fp.name
#     info = await classify_and_lookup(img_path=path)
#     await reply_text(event.reply_token,
#                      format_nutrition(info) if info else "這張圖認不出是什麼食物 QQ")

# async def reply_text(token, text):
#     await line_bot.reply_message(
#         ReplyMessageRequest(reply_token=token,
#                             messages=[TextMessage(text=text)])
#     )
