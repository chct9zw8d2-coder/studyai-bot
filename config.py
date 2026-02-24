import os

def _env(key: str, default=None):
    v = os.getenv(key)
    return v if (v is not None and v != "") else default

def _env_int(key: str, default: int) -> int:
    try:
        return int(_env(key, default))
    except Exception:
        return default

def _env_float(key: str, default: float) -> float:
    try:
        return float(_env(key, default))
    except Exception:
        return default

def _env_bool(key: str, default: bool) -> bool:
    v = _env(key, None)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

# -----------------------------
# Core
# -----------------------------
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
DATABASE_URL = _env("DATABASE_URL")

# Owner/admin
OWNER_USER_ID = _env_int("OWNER_USER_ID", 0)
ADMIN_CHAT_ID = _env_int("ADMIN_CHAT_ID", 0)

# Free limits
FREE_TEXT_PER_DAY = _env_int("FREE_TEXT_PER_DAY", 10)
FREE_IMG_PER_DAY  = _env_int("FREE_IMG_PER_DAY", 3)

# Stars / payments
PRICE_STARS = _env_int("PRICE_STARS", 299)     # базовая цена (если где-то используется)
SUB_DAYS    = _env_int("SUB_DAYS", 30)         # длительность подписки в днях
STARS_CURRENCY = _env("STARS_CURRENCY", "XTR") # обычно "XTR" для Stars

# -----------------------------
# DeepSeek (text + vision)
# -----------------------------
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Модели можно менять через Railway variables
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", _env("TEXT_MODEL", "deepseek-chat"))
DEEPSEEK_VISION_MODEL = _env("DEEPSEEK_VISION_MODEL", _env("VISION_MODEL", "deepseek-vl"))

# Для совместимости со старым кодом
TEXT_MODEL = DEEPSEEK_MODEL
VISION_MODEL = DEEPSEEK_VISION_MODEL

# -----------------------------
# Stability (images)
# -----------------------------
STABILITY_API_KEY = _env("STABILITY_API_KEY")
# если в коде где-то ожидается IMAGE_MODEL — оставим, но по факту у нас генерация через Stability
IMAGE_MODEL = _env("IMAGE_MODEL", "stability")

# -----------------------------
# Monetization / referral (чтобы db.py и bot.py не падали)
# -----------------------------
REF_PERCENT = _env_float("REF_PERCENT", 0.10)                 # 10% по умолчанию
MIN_PAYOUT_STARS = _env_int("MIN_PAYOUT_STARS", 2000)         # минималка на вывод
PAYOUT_COOLDOWN_HOURS = _env_int("PAYOUT_COOLDOWN_HOURS", 72) # кулдаун на вывод
REF_REQUIRE_FIRST_PAYMENT = _env_bool("REF_REQUIRE_FIRST_PAYMENT", True)

# Старое имя, из-за которого у тебя падало:
SUBSCRIBE_DAYS_DEFAULT = _env_int("SUBSCRIBE_DAYS_DEFAULT", SUB_DAYS)

# Тарифы подписки — если код ожидает PLANS
# Ставь свои цены (stars) и лимиты, главное — чтобы структура была.
PLANS = {
    "START": {
        "title": "START",
        "price_stars": _env_int("PLAN_START_PRICE", 299),
        "days": _env_int("PLAN_START_DAYS", 30),
        "text_per_day": _env_int("PLAN_START_TEXT_PER_DAY", 80),
        "img_per_day": _env_int("PLAN_START_IMG_PER_DAY", 10),
    },
    "PRO": {
        "title": "PRO",
        "price_stars": _env_int("PLAN_PRO_PRICE", 599),
        "days": _env_int("PLAN_PRO_DAYS", 30),
        "text_per_day": _env_int("PLAN_PRO_TEXT_PER_DAY", 250),
        "img_per_day": _env_int("PLAN_PRO_IMG_PER_DAY", 25),
    },
    "ULTRA": {
        "title": "ULTRA",
        "price_stars": _env_int("PLAN_ULTRA_PRICE", 999),
        "days": _env_int("PLAN_ULTRA_DAYS", 30),
        "text_per_day": _env_int("PLAN_ULTRA_TEXT_PER_DAY", 9999),
        "img_per_day": _env_int("PLAN_ULTRA_IMG_PER_DAY", 9999),
    },
}

# -----------------------------
# Safety checks (чтобы сразу понять что не так)
# -----------------------------
def validate_config():
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is missing")
    if not DATABASE_URL:
        errors.append("DATABASE_URL is missing")
    if not DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY is missing")
    if not STABILITY_API_KEY:
        errors.append("STABILITY_API_KEY is missing")
    return errors
