import os, pathlib, re, json, pandas as pd, httpx, functools
from dotenv import load_dotenv

load_dotenv()

CSV = pathlib.Path(__file__).with_name("nutrition.csv")
CSV.touch(exist_ok=True)

# ---------- 讀現有 CSV -------------------------------------------------
if CSV.stat().st_size == 0:        # 完全空檔 → 建欄位
    df = pd.DataFrame(columns=["name", "kcal", "protein", "fat", "carb"])
    df.to_csv(CSV, index=False)
else:
    df = pd.read_csv(CSV)

# ---------- 簡單的 normalize ------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())

# ---------- 查本機 ----------------------------------------------------
def lookup_food(name: str):
    key = _norm(name)
    row = df[df["name"].apply(_norm) == key]
    if row.empty:
        return None
    row = row.iloc[0]
    return dict(
        name=row["name"],
        calories=row["kcal"],
        protein=row["protein"],
        fat=row["fat"],
        carbs=row["carb"],
    )

# ---------- 叫 Spoonacular API ---------------------------------------
_API = "https://api.spoonacular.com/food/ingredients/search"
_DETAILS = "https://api.spoonacular.com/food/ingredients/{id}/information"
_KEY = os.getenv("SPOONACULAR_API_KEY", "")

async def fetch_nutrition(name: str):
    if not _KEY:
        return None

    async with httpx.AsyncClient(timeout=10) as client:
        # 1) 先搜尋 id
        try:
            resp = await client.get(_API, params={"query": name, "apiKey": _KEY, "number": 1})
            resp.raise_for_status()
            items = resp.json().get("results", [])
            if not items:
                return None
            iid = items[0]["id"]
            # 2) 取營養
            resp = await client.get(_DETAILS.format(id=iid), params={"amount": 100, "unit": "g", "apiKey": _KEY})
            resp.raise_for_status()
            info = resp.json()
        except Exception as e:
            print("[nutrition_db] API error:", e, flush=True)
            return None

    nutr = {n["name"]: n["amount"] for n in info["nutrition"]["nutrients"]}
    data = dict(
        name=info["name"],
        calories=round(nutr.get("Calories", 0), 1),
        protein=round(nutr.get("Protein", 0), 1),
        fat=round(nutr.get("Fat", 0), 1),
        carbs=round(nutr.get("Carbohydrates", 0), 1),
    )

    # 3) append 到 CSV 做快取
    global df
    df = pd.concat([df, pd.DataFrame([{
        "name": data["name"],
        "kcal": data["calories"],
        "protein": data["protein"],
        "fat": data["fat"],
        "carb": data["carbs"],
    }])], ignore_index=True)
    df.to_csv(CSV, index=False)

    return data
