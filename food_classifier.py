import torch, os, asyncio, tempfile
from transformers import AutoProcessor, ViTForImageClassification
from nutrition_db import lookup_food, fetch_nutrition

# ---------- 模型 ------------------------------------------------------
MODEL = "nateraw/food101-vit-base-patch16-224"
device = "cpu"

processor = AutoProcessor.from_pretrained(MODEL)
model     = ViTForImageClassification.from_pretrained(MODEL).to(device).eval()

# ---------- 圖片 → class name ----------------------------------------
@torch.inference_mode()
def _classify_image(path: str):
    from PIL import Image
    img = Image.open(path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt").to(device)
    logits = model(**inputs).logits[0]
    idx = logits.argmax().item()
    prob = torch.softmax(logits, dim=0)[idx].item()
    return model.config.id2label[idx], prob

# ---------- 封裝：圖片或文字 → 營養 dict -------------------------------
async def classify_and_lookup(img_path: str = None, text: str = None):
    if text:                                   # ── 純文字（直接查）
        info = lookup_food(text)
        if info:
            return info
        return await fetch_nutrition(text)

    if img_path:                               # ── 圖片
        name, p = _classify_image(img_path)
        print(f"[Debug] classify = {name}, prob={p:.3f}", flush=True)
        info = lookup_food(name)
        if info:
            return info
        return await fetch_nutrition(name)
