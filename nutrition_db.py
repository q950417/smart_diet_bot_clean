import os, pathlib, re, pandas as pd, httpx
from dotenv import load_dotenv
load_dotenv()

CSV = pathlib.Path(__file__).with_name("nutrition.csv")
CSV.touch(exist_ok=True)

if CSV.stat().st_size == 0:          # 建欄位
    pd.DataFrame(columns=["name", "kcal", "protein", "fat", "carb"]).to_csv(CSV, index=False)

df = pd.read_csv(CSV)                # 讀快取

# ---------- 工具 ----------
_norm = lambda s: re.sub(r"[^a-z]", "", s.lower())

def lookup_food(name: str):
    row = df[df["name"].apply(_norm) == _norm(name)]
    if row.empty:
        return None
    r = row.iloc[0]
    return dict(name=r["name"], calories=r["kcal"], protein=r["protein"], fat=r["fat"], carbs=r["carb"])

# ---------- Spoonacular ----------
_API1 = "https://api.spoonacular.com/food/ingredients/search"
_API2 = "https://api.spoonacular.com/food/ingredients/{id}/information"
_KEY  = os.getenv("SPOONACULAR_API_KEY", "")

async def fetch_nutrition(name: str):
    if not _KEY:
        return None
    async with httpx.AsyncClient(timeout=10) as cli:
        try:
            q = {"query": name, "number": 1, "apiKey": _KEY}
            r = await cli.get(_API1, params=q); r.raise_for_status()
            items = r.json()["results"];  iid = items[0]["id"]
            r = await cli.get(_API2.format(id=iid), params={"amount": 100, "unit": "g", "apiKey": _KEY})
            r.raise_for_status(); info = r.json()
        except Exception as e:
            print("[Spoonacular error]", e, flush=True)
            return None

    nutr = {n["name"]: n["amount"] for n in info["nutrition"]["nutrients"]}
    data = dict(
        name      = info["name"],
        calories  = round(nutr.get("Calories",        0), 1),
        protein   = round(nutr.get("Protein",         0), 1),
        fat       = round(nutr.get("Fat",             0), 1),
        carbs     = round(nutr.get("Carbohydrates",   0), 1),
    )

    # 寫回快取
    global df
    df = pd.concat([df, pd.DataFrame([{
        "name": data["name"], "kcal": data["calories"],
        "protein": data["protein"], "fat": data["fat"], "carb": data["carbs"]
    }])], ignore_index=True)
    df.to_csv(CSV, index=False)
    return data
