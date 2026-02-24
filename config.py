# config.py
import os


def _get(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def _get_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v is not None and v != "" else default
    except Exception:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


# -----------------------------
# Required envs (Railway)
# -----------------------------
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", "")

DATABASE_URL = _get("DATABASE_URL", "")

OWNER_USER_ID = _get_int("OWNER_USER_ID", 0)
ADMIN_CHAT_ID = _get_int("ADMIN_CHAT_ID", 0)

# -----------------------------
# Models / Providers
# -----------------------------
# DeepSeek (text + vision)
DEEPSEEK_API_KEY = _get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# В твоих переменных есть TEXT_MODEL / IMAGE_MODEL — оставляем совместимость:
TEXT_MODEL = _get("TEXT_MODEL", "deepseek-chat")
IMAGE_MODEL = _get("IMAGE_MODEL", "flux")

# bot.py импортирует DEEPSEEK_MODEL и DEEPSEEK_MODEL_FREE
DEEPSEEK_MODEL = _get("DEEPSEEK_MODEL", TEXT_MODEL or "deepseek-chat")
# Если хочешь отдельную "дешёвую" модель для free — просто задай в env DEEPSEEK_MODEL_FREE
DEEPSEEK_MODEL_FREE = _get("DEEPSEEK_MODEL_FREE", DEEPSEEK_MODEL)

DEEPSEEK_VISION_MODEL = _get("DEEPSEEK_VISION_MODEL", "deepseek-vl")

# -----------------------------
# Stability AI (images)
# -----------------------------
STABILITY_API_KEY = _get("STABILITY_API_KEY", "")
# Важно: bot.py и stability_image.py ожидают переменную STABILITY_ENDPOINT
# По умолчанию — Stable Image (Core). Можно переопределить в Railway переменной STABILITY_ENDPOINT.
STABILITY_ENDPOINT = _get(
    "STABILITY_ENDPOINT",
    "https://api.stability.ai/v2beta/stable-image/generate/core",
)
STABILITY_OUTPUT_FORMAT = _get("STABILITY_OUTPUT_FORMAT", "png")

# -----------------------------
# Telegram Stars payments
# -----------------------------
STARS_CURRENCY = _get("STARS_CURRENCY", "XTR")  # Telegram Stars currency code

# -----------------------------
# Limits / Plans
# -----------------------------
# Можно управлять лимитами через env:
FREE_TEXT_PER_DAY = _get_int("FREE_TEXT_PER_DAY", 3)
FREE_IMG_PER_DAY = _get_int("FREE_IMG_PER_DAY", 1)

SUB_DAYS = _get_int("SUB_DAYS", 30)  # длительность подписки в днях
PRICE_STARS = _get_int("PRICE_STARS", 299)  # цена START по умолчанию

PLANS = {
    "free": {
        "name": {"ru": "FREE", "en": "FREE"},
        "price_stars": 0,
        "days": 0,
        "daily_text": FREE_TEXT_PER_DAY,
        "daily_img": FREE_IMG_PER_DAY,
    },
    "start": {
        "name": {"ru": "START", "en": "START"},
        "price_stars": PRICE_STARS,
        "days": SUB_DAYS,
        "daily_text": 30,
        "daily_img": 10,
    },
    # Спец-тариф для first purchase (если используешь)
    "start_first": {
        "name": {"ru": "START (первый платёж)", "en": "START (first purchase)"},
        "price_stars": max(1, PRICE_STARS - 50),
        "days": SUB_DAYS,
        "daily_text": 30,
        "daily_img": 10,
    },
    "pro": {
        "name": {"ru": "PRO", "en": "PRO"},
        "price_stars": _get_int("PRICE_STARS_PRO", 599),
        "days": SUB_DAYS,
        "daily_text": 80,
        "daily_img": 25,
    },
    "ultra": {
        "name": {"ru": "ULTRA", "en": "ULTRA"},
        "price_stars": _get_int("PRICE_STARS_ULTRA", 999),
        "days": SUB_DAYS,
        "daily_text": 200,
        "daily_img": 60,
    },
}

# -----------------------------
# Topups (покупка пакетов)
# -----------------------------
TOPUPS = {
    "mini": {
        "title": {"ru": "Мини-пакет", "en": "Mini pack"},
        "stars": _get_int("TOPUP_MINI_STARS", 79),
        "add_text": _get_int("TOPUP_MINI_ADD_TEXT", 15),
        "add_img": _get_int("TOPUP_MINI_ADD_IMG", 3),
    },
    "plus": {
        "title": {"ru": "Плюс-пакет", "en": "Plus pack"},
        "stars": _get_int("TOPUP_PLUS_STARS", 149),
        "add_text": _get_int("TOPUP_PLUS_ADD_TEXT", 35),
        "add_img": _get_int("TOPUP_PLUS_ADD_IMG", 7),
    },
    "max": {
        "title": {"ru": "Макс-пакет", "en": "Max pack"},
        "stars": _get_int("TOPUP_MAX_STARS", 249),
        "add_text": _get_int("TOPUP_MAX_ADD_TEXT", 70),
        "add_img": _get_int("TOPUP_MAX_ADD_IMG", 15),
    },
    # "week_pack" используется в bot.py как спец-оффер (A/B), оставляем как базовый fallback
    "week_pack": {
        "title": {"ru": "Недельный пак", "en": "Weekly pack"},
        "stars": _get_int("TOPUP_WEEK_STARS", 199),
        "add_text": _get_int("TOPUP_WEEK_ADD_TEXT", 50),
        "add_img": _get_int("TOPUP_WEEK_ADD_IMG", 10),
    },
}

# -----------------------------
# Monetization / referrals / payouts
# -----------------------------
REF_PERCENT = _get_int("REF_PERCENT", 20)  # процент реферального начисления
MIN_PAYOUT_STARS = _get_int("MIN_PAYOUT_STARS", 300)
PAYOUT_COOLDOWN_HOURS = _get_int("PAYOUT_COOLDOWN_HOURS", 72)
REF_REQUIRE_FIRST_PAYMENT = _get_bool("REF_REQUIRE_FIRST_PAYMENT", True)

# bot.py импортирует REVENUE_DAYS_DEFAULT
REVENUE_DAYS_DEFAULT = _get_int("REVENUE_DAYS_DEFAULT", 7)

# -----------------------------
# Tokens / caching
# -----------------------------
# bot.py импортирует MAX_TOKENS как dict и потом делает MAX_TOKENS.get(plan_key, ...)
MAX_TOKENS = {
    "free": _get_int("MAX_TOKENS_FREE", 700),
    "start": _get_int("MAX_TOKENS_START", 1200),
    "pro": _get_int("MAX_TOKENS_PRO", 1600),
    "ultra": _get_int("MAX_TOKENS_ULTRA", 2200),
}

ENABLE_TEXT_CACHE = _get_bool("ENABLE_TEXT_CACHE", True)
ENABLE_IMAGE_CACHE = _get_bool("ENABLE_IMAGE_CACHE", False)  # если появится image-cache
TEXT_CACHE_TTL_DAYS = _get_int("TEXT_CACHE_TTL_DAYS", 30)
IMAGE_CACHE_TTL_DAYS = _get_int("IMAGE_CACHE_TTL_DAYS", 30)
