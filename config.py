# config.py
import os

def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    if v is None:
        return default
    v = v.strip()
    return v if v != "" else default

def _env_int(key: str, default: int) -> int:
    v = _env(key)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default

def _env_bool(key: str, default: bool = False) -> bool:
    v = _env(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")

# --- Required / main ---
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = _env("DATABASE_URL", _env("DATABASE_URL".lower(), "")) or ""

# Модели (то, что ты задаёшь в Railway Variables)
TEXT_MODEL = _env("TEXT_MODEL", "openai")          # например: openai / deepseek
IMAGE_MODEL = _env("IMAGE_MODEL", "flux")         # например: flux / sd3 / stability

# --- DeepSeek ---
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL = _env("DEEPSEEK_VISION_MODEL", "deepseek-vl")

# --- Stability (картинки) ---
STABILITY_API_KEY = _env("STABILITY_API_KEY", "")

# Если в боте выбран flux — по умолчанию ставим flux endpoint (можешь переопределить переменной STABILITY_ENDPOINT)
_default_stability_endpoint = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
if (IMAGE_MODEL or "").lower() == "flux":
    _default_stability_endpoint = "https://api.stability.ai/v2beta/stable-image/generate/flux"

STABILITY_ENDPOINT = _env("STABILITY_ENDPOINT", _default_stability_endpoint)

# --- Limits / cache ---
MAX_TOKENS = _env_int("MAX_TOKENS", 1000)

ENABLE_TEXT_CACHE = _env_bool("ENABLE_TEXT_CACHE", True)
TEXT_CACHE_TTL_DAYS = _env_int("TEXT_CACHE_TTL_DAYS", 7)

ENABLE_IMAGE_CACHE = _env_bool("ENABLE_IMAGE_CACHE", True)
IMAGE_CACHE_TTL_DAYS = _env_int("IMAGE_CACHE_TTL_DAYS", 7)

# --- Monetization / referrals ---
REF_PERCENT = _env_int("REF_PERCENT", 20)              # % от пополнений/покупок
MIN_PAYOUT_STARS = _env_int("MIN_PAYOUT_STARS", 1000)  # минимум к выводу
PAYOUT_COOLDOWN_HOURS = _env_int("PAYOUT_COOLDOWN_HOURS", 24)
REF_REQUIRE_FIRST_PAYMENT = _env_bool("REF_REQUIRE_FIRST_PAYMENT", True)

# --- Plans / Topups ---
# Можно оставить дефолты — они просто нужны, чтобы bot.py не падал при импорте.
# Если хочешь, поменяй цены/лимиты под себя.

SUB_DAYS = _env_int("SUB_DAYS", 30)
PRICE_STARS = _env_int("PRICE_STARS", 299)  # базовая цена (если используешь одну)

PLANS = {
    # В bot.py явно используется PLANS["start"] и PLANS["start_first"]
    "start_first": {
        "name": {"ru": "START (первый раз)", "en": "START (first time)"},
        "price_stars": PRICE_STARS,
        "days": SUB_DAYS,
        "daily_text": _env_int("FREE_TEXT_PER_DAY", 20),
        "daily_img": _env_int("FREE_IMG_PER_DAY", 3),
    },
    "start": {
        "name": {"ru": "START", "en": "START"},
        "price_stars": PRICE_STARS,
        "days": SUB_DAYS,
        "daily_text": _env_int("FREE_TEXT_PER_DAY", 20),
        "daily_img": _env_int("FREE_IMG_PER_DAY", 3),
    },
    "pro": {
        "name": {"ru": "PRO", "en": "PRO"},
        "price_stars": _env_int("PRO_PRICE_STARS", 599),
        "days": SUB_DAYS,
        "daily_text": _env_int("PRO_TEXT_PER_DAY", 200),
        "daily_img": _env_int("PRO_IMG_PER_DAY", 20),
    },
    "ultra": {
        "name": {"ru": "ULTRA", "en": "ULTRA"},
        "price_stars": _env_int("ULTRA_PRICE_STARS", 999),
        "days": SUB_DAYS,
        "daily_text": _env_int("ULTRA_TEXT_PER_DAY", 1000),
        "daily_img": _env_int("ULTRA_IMG_PER_DAY", 100),
    },
}

TOPUPS = {
    # bot.py ожидает структуру: TOPUPS[key]["title"]["ru"], TOPUPS[key]["stars"]
    "small": {"title": {"ru": "Пополнить 100 ⭐", "en": "Top up 100 ⭐"}, "stars": 100},
    "mid": {"title": {"ru": "Пополнить 300 ⭐", "en": "Top up 300 ⭐"}, "stars": 300},
    "big": {"title": {"ru": "Пополнить 1000 ⭐", "en": "Top up 1000 ⭐"}, "stars": 1000},
}

# Полезно, чтобы в логах сразу было видно что config реально подхватился
print("Config loaded")
print("TEXT_MODEL:", TEXT_MODEL)
print("IMAGE_MODEL:", IMAGE_MODEL)
print("MAX_TOKENS:", MAX_TOKENS)
