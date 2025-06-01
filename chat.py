def nutrition_only_reply(info: dict | None, query: str) -> str:
    """
    - info = 營養 dict（有值就用），None 表示查不到  
    - query = 使用者原文字／"這張照片"
    """
    if not info:
        return f"抱歉，看不出「{query}」是什麼食物 QQ"

    return (
        f"\n"
        f"熱量：{info['calories']} kcal\n"
        f"蛋白質：{info['protein']} g｜脂肪：{info['fat']} g｜碳水：{info['carbs']} g\n"
        "（數值為估算，僅供參考）"
    )
