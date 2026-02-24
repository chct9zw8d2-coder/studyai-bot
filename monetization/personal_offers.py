
import datetime as dt
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import PLANS

OFFER_COOLDOWN_HOURS = 6
PROMO_TTL_MINUTES = 60

# Bonuses granted on purchase when promo is active
PROMO_BONUSES = {
    "start_boost": {"add_text": 30, "add_img": 0},
    "pro_boost":   {"add_text": 80, "add_img": 0},
    "ultra_boost": {"add_text": 200, "add_img": 0},
}

def _kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⭐ Выбрать тариф", callback_data="menu:sub")]])

def choose_offer(plan_key: str, text_used: int, img_used: int, daily_text: int, daily_img: int):
    """
    Returns (promo_kind, target_plan) or (None, None)
    """
    if plan_key == "free":
        # If they are engaged, push START first, then PRO
        if text_used >= 12:
            return ("pro_boost", "pro")
        if text_used >= 6:
            return ("start_boost", "start")
        # If they tried images (should be 0 on free) or are in image mode
        return (None, None)
    if plan_key == "start":
        # nearing limits => PRO
        if daily_text and text_used >= int(daily_text * 0.7):
            return ("pro_boost", "pro")
    if plan_key == "pro":
        if daily_text and text_used >= int(daily_text * 0.7):
            return ("ultra_boost", "ultra")
    return (None, None)

def build_offer_text(lang: str, promo_kind: str, target_plan: str, focus_text: str = ""):
    bonus = PROMO_BONUSES.get(promo_kind, {})
    add_text = bonus.get("add_text", 0)

    plan = PLANS.get(target_plan, {})
    price = plan.get("price_stars", 0)
    plan_name = plan.get("name", {}).get(lang, target_plan.upper())

    lines = []
    lines.append("🎁 Персональное предложение")
    lines.append("")
    lines.append(f"Активируй {plan_name} в течение {PROMO_TTL_MINUTES} минут и получи бонус:")
    if add_text:
        lines.append(f"• +{add_text} ответов сегодня")
    lines.append("")
    lines.append(f"Цена: {price}⭐ / месяц")
    return "\n".join(lines)

def offer_keyboard():
    return _kb()

def promo_expires_at():
    return dt.datetime.utcnow() + dt.timedelta(minutes=PROMO_TTL_MINUTES)
