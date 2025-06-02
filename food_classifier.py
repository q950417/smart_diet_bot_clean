# # food_classifier.py
# import os, asyncio, tempfile, httpx, pandas as pd, backoff

# # Spoonacular base url & key
# BASE = "https://api.spoonacular.com"
# API_KEY = os.getenv("SPOONACULAR_KEY", "")

# if not API_KEY:
#     raise RuntimeError(
#         "❌ 失敗：環境變數 SPOONACULAR_KEY 沒設定！\n"
#         "‣ 在 .env 寫：SPOONACULAR_KEY=xxxxxxxxxxxxxxxx\n"
#         "‣ Render Dashboard → Environment 也要加同名變數"
#     )

# # -------------- util ----------------
# @backoff.on_exception(backoff.expo, httpx.HTTPStatusError, max_tries=3)
# async def _get(path: str, **params) -> dict:
#     """對 spoonacular GET，若 402 代表配額用完，401 代表 key 無效/沒帶。"""
#     params["apiKey"] = API_KEY
#     async with httpx.AsyncClient(timeout=30) as client:
#         r = await client.get(f"{BASE}{path}", params=params)
#     r.raise_for_status()
#     return r.json()

# async def _guess_nutrition(name: str) -> dict | None:
#     j = await _get(f"{BASE}/recipes/guessNutrition", title=name)
#     if not j:
#         return None
#     return {
#         "name": name,
#         "calories": int(j["calories"]["value"]),
#         "protein" : int(j["protein"]["value"]),
#         "fat"     : int(j["fat"]["value"]),
#         "carbs"   : int(j["carbs"]["value"]),
#     }

# async def _guess_image_nutrition(path: str) -> dict | None:
#     mime = mimetypes.guess_type(path)[0] or "image/jpeg"
#     files  = {"file": (path, open(path, "rb"), mime)}
#     params = {"apiKey": KEY}

#     async with httpx.AsyncClient(timeout=60) as c:
#         r = await c.post(f"{BASE}/food/images/analyze", params=params, files=files)
#     r.raise_for_status()
#     j = r.json()

#     # 若信心度過低就當作「無法辨識」
#     conf = j.get("category", {}).get("confidence") or 1.0
#     if conf < 0.30:
#         return None

#     name = j["category"]["name"]
#     nuts = {n["name"].lower(): n["amount"] for n in
#             j.get("nutrition", {}).get("nutrients", [])}

#     return {
#         "name": name,
#         "calories": int(nuts.get("calories", 0)),
#         "protein" : int(nuts.get("protein", 0)),
#         "fat"     : int(nuts.get("fat", 0)),
#         "carbs"   : int(nuts.get("carbohydrates", 0)),
#     }


# # ------------------- CSV 快取 ---------------------

# def _lookup_local(name: str) -> dict | None:
#     global _df
#     m = _df["name"].str.lower() == name.lower()
#     if m.any():
#         return _df.loc[m].iloc[0].to_dict()
#     return None

# def _cache(info: dict):
#     global _df
#     if (_df["name"].str.lower() == info["name"].lower()).any():
#         return
#     _df.loc[len(_df)] = info
#     _df.to_csv(CSV, index=False)


# # ------------------- 對外函式 ----------------------

# async def classify_and_lookup(*,
#                               text: str | None = None,
#                               img_path: str | None = None) -> dict | None:
#     if text:
#         if (info := _lookup_local(text)):
#             return info
#         info = await _guess_nutrition(text)

#     elif img_path:
#         info = await _guess_image_nutrition(img_path)
#         # 若圖片辨識出了名稱，再嘗試 CSV / API 精修
#         if info and info["name"]:
#             info = _lookup_local(info["name"]) or info

#     else:
#         info = None

#     if info:
#         _cache(info)

#     return info

#======================================
# food_classifier.py
import os, asyncio, pandas as pd, httpx, pathlib

BASE = "https://api.spoonacular.com"
CSV  = pathlib.Path(__file__).with_name("nutrition_db.csv")  # 你的離線資料表
API_KEY = os.getenv("SPOONACULAR_KEY", "")

# ── 小工具 ───────────────────────────────────────────────
async def _get_json(path: str, **params) -> dict | None:
    """統一 GET；逾時或 4xx/5xx 都回 None"""
    params["apiKey"] = API_KEY
    url = f"{BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:  # 把 timeout 拉長
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        print("[Nutrition-API]", e)
        return None

# ── 文字→營養（只靠 API；失敗就 None）────────────────────
async def _guess_nutrition(name: str) -> dict | None:
    data = await _get_json("/recipes/guessNutrition", title=name)
    if not data or "status" in data:      # API 回 'status': 'failure' 也算失敗
        return None
    return {
        "name": name,
        "calories": round(data["calories"]["value"]),
        "protein":  round(data["protein"]["value"]),
        "fat":      round(data["fat"]["value"]),
        "carbs":    round(data["carbs"]["value"]),
    }

# ── 離線 CSV 快速查找 ─────────────────────────────────────
_df = pd.read_csv(CSV) if CSV.exists() else pd.DataFrame()

def _lookup_local(name: str) -> dict | None:
    row = _df.loc[_df["name"].str.lower() == name.lower()]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "name": r["name"],
        "calories": int(r["calories"]),
        "protein":  int(r["protein"]),
        "fat":      int(r["fat"]),
        "carbs":    int(r["carbs"]),
    }

# ── 對外主函式 ─────────────────────────────────────────────
async def classify_and_lookup(*, text: str | None = None,
                              img_path: str | None = None) -> dict | None:
    """
    - 文字：直接當做食物名稱去查
    - 圖片：這裡簡化，之後可接入模型辨識；先回 None
    """
    name = text.strip() if text else None
    if not name:
        return None

    # 1) 先用離線資料庫
    if (info := _lookup_local(name)):
        return info

    # 2) 再嘗試調 API（可能會逾時 / 額度不足）
    return await _guess_nutrition(name)


=============================================
"""
純 Spoonacular 版本：
* 文字：/recipes/guessNutrition?title=<food name>
* 圖片：/food/images/analyze  → 再把識別出的名稱丟到 guessNutrition
"""
import os, httpx, asyncio, tempfile, base64

API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
BASE    = "https://api.spoonacular.com"

async def _get_json(url: str, **params):
    params["apiKey"] = API_KEY
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params)
    r.raise_for_status()
    return r.json()

async def _post_image(image_path: str):
    url = f"{BASE}/food/images/analyze"
    params = {"apiKey": API_KEY}
    with open(image_path, "rb") as fp:
        files = {"file": fp}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, params=params, files=files)
    r.raise_for_status()
    return r.json()

async def _guess_nutrition(name: str):
    data = await _get_json(f"{BASE}/recipes/guessNutrition", title=name)
    if not data.get("calories"):          # 找不到營養就 None
        return None
    return {
        "name"     : name.title(),
        "calories" : round(data["calories"]["value"]),
        "protein"  : round(data["protein"]["value"], 1),
        "fat"      : round(data["fat"]["value"], 1),
        "carbs"    : round(data["carbs"]["value"], 1),
    }

# ── 對外 ───────────────────────────────────────────────────
async def classify_and_lookup(*, text: str | None = None,
                              img_path: str | None = None):
    if text:                              # 文字直接估營養
        return await _guess_nutrition(text)

    if img_path:                          # 圖片 → 類別 → 營養
        try:
            res  = await _post_image(img_path)
            label = res["category"]["name"]          # Food-101 類別名稱
        except Exception:
            return None
        return await _guess_nutrition(label)

    return None            # 兩個都沒給
