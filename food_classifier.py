import os, pathlib, json, asyncio, httpx
from dotenv import load_dotenv; load_dotenv()

# 你的 Spoonacular key
SPOON_KEY = os.getenv("SPOONACULAR_API_KEY")

# ─── 用 Spoonacular 食物分類 + 營養估算 ────────────────
async def classify_and_lookup(img_path: str = None, text: str = None):
    assert SPOON_KEY, "SPOONACULAR_API_KEY 未設定！"

    async with httpx.AsyncClient(timeout=30) as cli:
        if img_path:      # 圖片 → classification
            url = "https://api.spoonacular.com/food/images/classify"
            files = {"file": open(img_path, "rb")}
            params = {"apiKey": SPOON_KEY}
            resp = await cli.post(url, files=files, params=params)
            data = resp.json()
            food_name = data.get("category")
            prob      = data.get("probability")
            print(f"[Debug] 圖片分類 → {food_name}, prob={prob}", flush=True)
        else:             # 純文字查詢
            food_name = text
            print(f"[Debug] 直接查文字 → {food_name}", flush=True)

        if not food_name:
            return None

        # 估算營養
        nutr_url = "https://api.spoonacular.com/recipes/guessNutrition"
        params   = {"title": food_name, "apiKey": SPOON_KEY}
        nutr     = (await cli.get(nutr_url, params=params)).json()

        if nutr.get("status") == "failure":
            return None

        return {
            "name":  food_name,
            "calories": nutr["calories"]["value"],
            "protein":  nutr["protein"]["value"],
            "fat":      nutr["fat"]["value"],
            "carbs":    nutr["carbs"]["value"],
        }
