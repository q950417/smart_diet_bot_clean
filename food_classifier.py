# food_classifier.py

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")   # ➡️ 一進來就載 .env

import os
import httpx
from typing import Optional, Dict

# 從 .env 拿 Spoonacular API Key
API_KEY = os.getenv("SPOONACULAR_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError("請先在 .env 裡設定 SPOONACULAR_API_KEY")

# Spoonacular 的 endpoint
IMAGE_CLASSIFY_URL  = "https://api.spoonacular.com/food/images/classify"
NUTRITION_GUESS_URL = "https://api.spoonacular.com/recipes/guessNutrition"

async def classify_and_lookup(img_path: str) -> Optional[Dict]:
    """
    1. 圖片分類 → 取得 data1["category"]
    2. 用 category 拿營養值 → 只提取 data2["calories"]["value"] 等純數字
    """
    # —— Step 1: 圖片分類 —— 
    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        files = {"file": ("image.jpg", img_bytes, "image/jpeg")}
        params_classify = {"apiKey": API_KEY}
        r1 = httpx.post(IMAGE_CLASSIFY_URL, params=params_classify, files=files, timeout=30.0)
        r1.raise_for_status()
        data1 = r1.json()
    except Exception as e:
        print("【Debug】圖片分類失敗，錯誤內容：", repr(e))
        return None

    # ➡️ 改正：直接拿 data1["category"]
    if not data1.get("category"):
        print("【Debug】分類 API 沒拿到 category：", data1)
        return None

    food_name = data1["category"].lower().strip()
    print(f"【Debug】分類結果 food_name = {food_name}，機率 = {data1.get('probability')}")

    # —— Step 2: 營養查詢 —— 
    try:
        params_nutrition = {"apiKey": API_KEY, "title": food_name}
        r2 = httpx.get(NUTRITION_GUESS_URL, params=params_nutrition, timeout=30.0)
        r2.raise_for_status()
        data2 = r2.json()
    except Exception as e:
        print("【Debug】營養查詢失敗，錯誤內容：", repr(e))
        print("【Debug】food_name =", food_name)
        return None

    # 確保營養 API 回傳有這四項
    if not all(k in data2 for k in ("calories", "protein", "fat", "carbs")):
        print("【Debug】營養 API 回傳不完整，data2 =", data2)
        return None

    # ➡️ 只擷取每個欄位裡的 .get("value")
    try:
        calories_val = data2["calories"].get("value")
        protein_val  = data2["protein"].get("value")
        fat_val      = data2["fat"].get("value")
        carbs_val    = data2["carbs"].get("value")
    except Exception as e:
        print("【Debug】無法擷取 value 欄位，data2 =", data2, "，錯誤：", repr(e))
        return None

    return {
        "name": food_name,
        "calories": calories_val,
        "protein": protein_val,
        "fat": fat_val,
        "carbs": carbs_val,
    }
