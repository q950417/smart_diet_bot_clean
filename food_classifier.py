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
