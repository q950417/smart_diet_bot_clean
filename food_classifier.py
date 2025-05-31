import os, httpx
from dotenv import load_dotenv
load_dotenv()

SPOON_KEY = os.getenv("SPOONACULAR_API_KEY")

async def classify_and_lookup(img_path: str = None, text: str = None):
    if not SPOON_KEY:
        return None

    async with httpx.AsyncClient(timeout=30) as cli:
        if img_path:
            files = {"file": open(img_path, "rb")}
            params = {"apiKey": SPOON_KEY}
            resp   = await cli.post(
                "https://api.spoonacular.com/food/images/classify",
                files=files, params=params)
            data = resp.json()
            food_name = data.get("category")
            print("[Debug] 圖片分類 →", food_name, flush=True)
        else:
            food_name = text
            print("[Debug] 直接查文字 →", food_name, flush=True)

        if not food_name:
            return None

        # 估算營養
        nutr = (await cli.get(
            "https://api.spoonacular.com/recipes/guessNutrition",
            params={"title": food_name, "apiKey": SPOON_KEY})
        ).json()

        if nutr.get("status") == "failure":
            return None

        # 必要欄位不齊 → 視為 None
        for key in ("calories", "protein", "fat", "carbs"):
            if key not in nutr:
                return None

        return {
            "name":     food_name,
            "calories": nutr["calories"]["value"],
            "protein":  nutr["protein"]["value"],
            "fat":      nutr["fat"]["value"],
            "carbs":    nutr["carbs"]["value"],
        }
