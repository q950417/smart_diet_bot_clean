# chat.py
import textwrap

# ── 1. 關鍵字聊天 ───────────────────────────
_GREETINGS = {"哈囉", "hello", "hi", "你好", "嗨"}

def try_greet(msg: str) -> str | None:
    """若 msg 為招呼語，回固定內容，否則回 None"""
    if msg.lower().strip() in _GREETINGS:
        return "嗨～今天想吃什麼呢？"
    return None


# ── 2. 依熱量給建議（純 if-else） ─────────────
def advice_by_calories(kcal: float) -> str:
    if kcal < 150:
        return "熱量不高，可以放心享用喔！"
    if kcal < 300:
        return "普通份量，記得均衡搭配蛋白質～"
    if kcal < 600:
        return "熱量稍高，建議搭配大量蔬菜或減少主食。"
    return "熱量偏高，建議分次食用或與朋友分享！"


# ── 3. 將營養 dict 轉成回覆文字 ──────────────
def format_nutrition(info: dict) -> str:
    txt = textwrap.dedent(f"""\
        {info['name']}（預估）
        熱量 {info['calories']} kcal
        蛋白質 {info['protein']} g　脂肪 {info['fat']} g　碳水 {info['carbs']} g

        {advice_by_calories(info['calories'])}
    """).strip()
    return txt
