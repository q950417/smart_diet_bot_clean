# chat.py  ──────────────────────────────────────────────────────────────
# 只做「關鍵字 → 回覆」與「排版營養結果」，完全不碰網路或 GPT。
# ----------------------------------------------------------------------

import re
from typing import Final, Dict

TRIGGERS: Final[Dict[str, str]] = {
    # ── 打招呼 ───────────────────────────────────────────────────────
    r"^(hi|hello)$":          "Hello! 😊  想查食物營養嗎？傳文字或照片給我吧！",
    r"^(哈囉|你好|嗨+)$":     "嗨嗨～請告訴我你吃了什麼，我來報營養！",
    # ── 生活化範例 ─────────────────────────────────────────────────
    r"謝謝":                  "不客氣～祝你用餐愉快！",
    r"(早安|good\s*morning)": "早安☀️  早餐記得均衡營養喔！",
    r"(晚安|good\s*night)":   "晚安～睡前別吃太多宵夜喔！",
    # ★ 想再加，就往下加 ------------------------------------------------
    # r"比薩":                 "比薩熱量通常不低，記得搭配蔬菜！",
}


def try_reply(text: str) -> str | None:
    """
    命中任一 TRIGGERS 就回覆；否則回 None 讓主程式去查營養。
    比對時一律轉小寫、去空白；正則用 IGNORECASE 。
    """
    t = text.strip().lower()
    for pattern, reply in TRIGGERS.items():
        if re.search(pattern, t, flags=re.IGNORECASE):
            return reply
    return None


# ── 以下是排版營養資訊 ────────────────────────────────────────────────
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
        f"蛋白質 {info['protein']} g | "
        f"脂肪 {info['fat']} g | "
        f"碳水 {info['carbs']} g\n"
        f"{advice_by_calories(info['calories'])}"
    )


#可以的
def try_greet(text: str) -> str | None:
    """
    如果使用者是在打招呼，就回固定字串；否則回 None
    """
    if text.lower() in {"hi", "hello", "哈囉", "你好"}:
        return "嗨！想知道食物的營養嗎？傳文字或照片給我吧！"
    return None


# ------------------------------------------------------------------------------


def advice_by_calories(kcal: int) -> str:
    """依熱量給簡單建議（純 if-else、不用 GPT）"""
    if kcal < 200:
        return "熱量很低，可以放心享用～"
    if kcal < 400:
        return "熱量中等，記得均衡飲食。"
    return "熱量偏高，建議搭配蔬菜或分次食用！"


def format_nutrition(info: dict) -> str:
    """把 Spoonacular 回傳的營養資訊排版成 Line 訊息"""
    return (
        f"{info['name']} 估算營養：\n"
        f"熱量 {info['calories']} kcal\n"
        f"蛋白質 {info['protein']} g | "
        f"脂肪 {info['fat']} g | "
        f"碳水 {info['carbs']} g\n"
        f"{advice_by_calories(info['calories'])}"
    )

#=========================================
# chat.py
# ────────────────────────────────────────────────
# 只處理最簡單的「關鍵字 → 固定回覆」邏輯，無 GPT 依賴
# ────────────────────────────────────────────────

# ===== 1) 文字觸發表 =====
# key  可以放多個同義字（用 | 分隔）或正規表達式
# val  就是要回給使用者的文字
# TRIGGERS: dict[str, str] = {
#     r"^(hi|hello)$":                    "Hello! 😊  想查食物營養嗎？傳文字或照片給我吧！",
#     r"^(哈囉|你好|嗨+)$":               "嗨嗨～請告訴我你吃了什麼，我來報營養！",
#     r"謝謝":                            "不客氣～祝你用餐愉快！",
#     r"(早安|good\s*morning)":           "早安☀️  早餐記得均衡營養喔！",
#     r"(晚安|good\s*night)":             "晚安～睡前別吃太多宵夜喔！",
#     # ↓ 自行追加
#     # r"比薩":                           "比薩熱量通常不低，記得搭配蔬菜！",
# }

# # ===== 2) 文字比對函式 =====
# import re

# def try_reply(text: str) -> str | None:
#     """
#     若符合任一觸發規則就回覆對應文字，否則回傳 None。
#     - 比對時一律轉成小寫、去掉空白，避免大小寫差異。
#     - 規則用 `re.IGNORECASE`，寫中文時不用在意大小寫。
#     """
#     t = text.strip().lower()
#     for pattern, reply in TRIGGERS.items():
#         if re.search(pattern, t, flags=re.IGNORECASE):
#             return reply
#     return None


# # ===== 3) 給營養結果時用的訊息格式 =====
# def advice_by_calories(kcal: int) -> str:
#     if kcal < 200:
#         return "熱量很低，可以放心享用～"
#     if kcal < 400:
#         return "熱量中等，記得均衡飲食。"
#     return "熱量偏高，建議搭配蔬菜或分次食用！"


# def format_nutrition(info: dict) -> str:
#     """把 food_classifier 回傳的 dict 轉成友善文字"""
#     return (
#         f"{info['name']} 估算營養：\n"
#         f"熱量 {info['calories']} kcal\n"
#         f"蛋白質 {info['protein']} g | 脂肪 {info['fat']} g | 碳水 {info['carbs']} g\n"
#         f"{advice_by_calories(info['calories'])}"
#     )



# # chat.py
# def try_greet(text: str) -> str | None:
#     if text.lower() in {"hi", "hello", "哈囉", "你好"}:
#         return "嗨！想知道食物的營養嗎？傳文字或照片給我吧！"
#     return None

# def advice_by_calories(kcal: int) -> str:
#     if kcal < 200:
#         return "熱量很低，可以放心享用～"
#     if kcal < 400:
#         return "熱量中等，記得均衡飲食。"
#     return "熱量偏高，建議搭配蔬菜或分次食用！"

# def format_nutrition(info: dict) -> str:
#     return (
#         f"{info['name']} 估算營養：\n"
#         f"熱量 {info['calories']} kcal\n"
#         f"蛋白質 {info['protein']} g | 脂肪 {info['fat']} g | 碳水 {info['carbs']} g\n"
#         f"{advice_by_calories(info['calories'])}"
#     )
