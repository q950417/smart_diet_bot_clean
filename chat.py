# chat.py
def try_greet(text: str) -> str | None:
    if text.lower() in {"hi", "hello", "哈囉", "你好"}:
        return "嗨！想知道食物的營養嗎？傳文字或照片給我吧！"
    return None

def advice_by_calories(kcal: int) -> str:
    if kcal < 200:
        return "熱量很低，可以放心享用～"
    if kcal < 400:
        return "熱量中等，記得均衡飲食。"
    return "熱量偏高，建議搭配蔬菜或分次食用！"

def format_nutrition(info: dict) -> str:
    return (
        f"{info['name']} 估算營養：\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g | 脂肪 {info['fat']} g | 碳水 {info['carbs']} g\n"
        f"{advice_by_calories(info['calories'])}"
    )
