import torch, tempfile, asyncio
from transformers import AutoProcessor, ViTForImageClassification
from nutrition_db import lookup_food, fetch_nutrition

MODEL  = "nateraw/food101-vit-base-patch16-224"
device = "cpu"

processor = AutoProcessor.from_pretrained(MODEL)
model     = ViTForImageClassification.from_pretrained(MODEL).to(device).eval()

@torch.inference_mode()
def _classify(path: str):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    inputs = processor(images=im, return_tensors="pt").to(device)
    logits = model(**inputs).logits[0]
    idx = logits.argmax().item()
    prob = torch.softmax(logits, dim=0)[idx].item()
    return model.config.id2label[idx], prob

async def classify_and_lookup(img_path: str = None, text: str = None):
    # ------- 純文字 -------
    if text:
        info = lookup_food(text)
        return info or await fetch_nutrition(text)

    # ------- 圖片 -------
    name, p = _classify(img_path)
    print(f"[Debug] classify={name} prob={p:.3f}", flush=True)
    info = lookup_food(name)
    return info or await fetch_nutrition(name)
