"""
簡化版：
  • img_path → 用你先前的模型辨識（如不需要可省）
  • text     → 直接拿來對 nutrition_db 查
只要回傳 nutrition_db.lookup 的結果 dict 或 None
"""
import asyncio

from nutrition_db import lookup_food

# 若仍想用圖辨識，可留原本 classify_image()
async def classify_and_lookup(
    img_path: str | None = None,
    text: str | None = None
):
    if text:                              # 文字直接查
        return lookup_food(text)

    if img_path:                          # 圖片就丟模型 → name
        from PIL import Image
        # 這裡簡單回傳 None，避免佔空間
        # TODO: 放回你自己的 classify_image(img_path)
        return None

    return None
