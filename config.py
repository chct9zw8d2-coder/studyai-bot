import os
from dataclasses import dataclass
from typing import Dict, Any


def _getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def _getenv_int(name: str, default: int) -> int:
    v = _getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _getenv_float(name: str, default: float) -> float:
    v = _getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _getenv_bool(name: str, default: bool) -> bool:
    v = _getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


# -----------------------
# Required / Core
# -----------------------
TELEGRAM_BOT_TOKEN = _getenv("TELEGRAM_BOT_TOKEN", "")  # must be set in Railway
DATABASE_URL = _getenv("DATABASE_URL")  # Railway Postgres provides it

OWNER_USER_ID = _getenv_int("OWNER_USER_ID", 0)
ADMIN_CHAT_ID = _getenv_int("ADMIN_CHAT_ID", 0)

STARS_CURRENCY = _getenv("STARS_CURRENCY", "XTR")  # Telegram Stars currency code


# -----------------------
# Models / Providers
# -----------------------
# Text model name used by your text backend
TEXT_MODEL = _getenv("TEXT_MODEL", _getenv("DEEPSEEK_MODEL", "deepseek-chat"))
# Compatibility: bot.py expects these names
DEEPSEEK_MODEL = _getenv("DEEPSEEK_MODEL", TEXT_MODEL)
DEEPSEEK_MODEL_FREE = _getenv("DEEPSEEK_MODEL_FREE", DEEPSEEK_MODEL)

DEEPSEEK_API_KEY = _getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_VISION_MODEL = _getenv("DEEPSEEK_VISION_MODEL", "deepseek-vl")

IMAGE_MODEL = _getenv("IMAGE_MODEL", "flux")  # you had flux in logs

# Stability (image)
STABILITY_API_KEY = _getenv("STABILITY_API_KEY", "")
STABILITY_ENDPOINT = _getenv("STABILITY_ENDPOINT", "https://api.stability.ai")  # <-- важно!


# -----------------------
# Limits / Cache
# -----------------------
MAX_TOKENS = _getenv_int("MAX_TOKENS", 1000)

FREE_TEXT_PER_DAY = _getenv_int("FREE_TEXT_PER_DAY", 10)
FREE_IMG_PER_DAY = _getenv_int("FREE_IMG_PER_DAY", 3)

ENABLE_TEXT_CACHE = _getenv_bool("ENABLE_TEXT_CACHE", True)
ENABLE_IMAGE_CACHE = _getenv_bool("ENABLE_IMAGE_CACHE", True)
TEXT_CACHE_TTL_DAYS = _getenv_int("TEXT_CACHE_TTL_DAYS", 7)
IMAGE_CACHE_TTL_DAYS = _getenv_int("IMAGE_CACHE_TTL_DAYS", 7)


# -----------------------
# Monetization / Plans
# -----------------------
# How many days subscription lasts
SUBSCRIBE_DAYS_DEFAULT = _getenv_int("SUB_DAYS", 30)
REVENUE_DAYS_DEFAULT = _getenv_int("REVENUE_DAYS_DEFAULT", 30)

# Referral / payouts (used by db.py in your logs)
REF_PERCENT = _getenv_float("REF_PERCENT", 0.15)  # 15% default
MIN_PAYOUT_STARS = _getenv_int("MIN_PAYOUT_STARS", 1000)
PAYOUT_COOLDOWN_HOURS = _getenv_int("PAYOUT_COOLDOWN_HOURS", 24)
REF_REQUIRE_FIRST_PAYMENT = _getenv_bool("REF_REQUIRE_FIRST_PAYMENT", True)

# Price in stars (your env var on Railway was PRICE_STARS)
PRICE_STARS = _getenv_int("PRICE_STARS", 299)

# Plans dict - bot.py imports PLANS
# Keys and fields are designed to be simple and stable.
PLANS: Dict[str, Dict[str, Any]] = {
    "START": {
        "title": "START",
        "stars": _getenv_int("PRICE_START_STARS", PRICE_STARS),  # default = PRICE_STARS
        "days": _getenv_int("DAYS_START", SUBSCRIBE_DAYS_DEFAULT),
    },
    "PRO": {
        "title": "PRO",
        "stars": _getenv_int("PRICE_PRO_STARS", 599),
        "days": _getenv_int("DAYS_PRO", SUBSCRIBE_DAYS_DEFAULT),
    },
    "ULTRA": {
        "title": "ULTRA",
        "stars": _getenv_int("PRICE_ULTRA_STARS", 999),
        "days": _getenv_int("DAYS_ULTRA", SUBSCRIBE_DAYS_DEFAULT),
    },
}

# Topups dict - bot.py imports TOPUPS
TOPUPS: Dict[str, Dict[str, Any]] = {
    "TOPUP_100": {"title": "Пополнение +100⭐", "stars": _getenv_int("TOPUP_100_STARS", 100)},
    "TOPUP_300": {"title": "Пополнение +300⭐", "stars": _getenv_int("TOPUP_300_STARS", 300)},
    "TOPUP_700": {"title": "Пополнение +700⭐", "stars": _getenv_int("TOPUP_700_STARS", 700)},
}


# -----------------------
# Startup sanity checks (НЕ падаем, только предупреждаем)
# -----------------------
def _warn(msg: str):
    # prints go to Railway logs
    print(f"[config] WARNING: {msg}")


if not TELEGRAM_BOT_TOKEN:
    _warn("TELEGRAM_BOT_TOKEN is empty. Bot will not start correctly.")

if DATABASE_URL is None:
    _warn("DATABASE_URL is not set (Postgres may not be connected).")

if IMAGE_MODEL.lower() in ("stability", "sd", "stable-diffusion") and not STABILITY_API_KEY:
    _warn("STABILITY_API_KEY is empty but IMAGE_MODEL suggests Stability usage.")
