# config.py
import os

def _env(name: str, default=None):
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v

def _env_int(name: str, default: int) -> int:
    v = _env(name, None)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default

def _env_float(name: str, default: float) -> float:
    v = _env(name, None)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    v = _env(name, None)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

# =========================
# Telegram
# =========================
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    # Лучше упасть с понятной ошибкой, чем молча
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN env var")

ADMIN_CHAT_ID = _env_int("ADMIN_CHAT_ID", 0)
OWNER_USER_ID = _env_int("OWNER_USER_ID", 0)

# =========================
# Database
# =========================
DATABASE_URL = _env("DATABASE_URL", "")
if not DATABASE_URL:
    # Если ты реально используешь Postgres — лучше требовать.
    # Если не используешь — можно убрать raise.
    raise RuntimeError("Missing DATABASE_URL env var")

# =========================
# Models / Providers
# =========================
# Текстовая модель (в твоих переменных есть TEXT_MODEL)
TEXT_MODEL = _env("TEXT_MODEL", "deepseek-chat")

# Для совместимости со старым кодом (часто используется как "провайдер/модель")
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", TEXT_MODEL)
DEEPSEEK_MODEL_FREE = _env("DEEPSEEK_MODEL_FREE", DEEPSEEK_MODEL)
DEEPSEEK_VISION_MODEL = _env("DEEPSEEK_VISION_MODEL", "deepseek-vision")

# =========================
# Image generation (Stability)
# =========================
STABILITY_API_KEY = _env("STABILITY_API_KEY", "")
# ВАЖНО: это имя у тебя просит код (в логах было can’t import STABILITY_ENDPOINT)
STABILITY_ENDPOINT = _env("STABILITY_ENDPOINT", "https://api.stability.ai")
# Формат выдачи (для stability_image.py)
STABILITY_OUTPUT_FORMAT = _env("STABILITY_OUTPUT_FORMAT", "png")

# Для твоих переменных Railway
IMAGE_MODEL = _env("IMAGE_MODEL", _env("IMAGE_MODEL", "flux"))

# =========================
# Limits / performance
# =========================
MAX_TOKENS = _env_int("MAX_TOKENS", 1000)

ENABLE_USER_CACHE = _env_bool("ENABLE_USER_CACHE", True)
ENABLE_DB_CACHE = _env_bool("ENABLE_DB_CACHE", True)

# =========================
# Freemium / subscription
# =========================
FREE_TEXT_PER_DAY = _env_int("FREE_TEXT_PER_DAY", 10)
FREE_IMG_PER_DAY = _env_int("FREE_IMG_PER_DAY", 3)

# Подписка (дней)
SUBSCRIBE_DAYS_DEFAULT = _env_int("SUBSCRIBE_DAYS_DEFAULT", _env_int("SUB_DAYS", 30))
SUB_DAYS = _env_int("SUB_DAYS", SUBSCRIBE_DAYS_DEFAULT)

# Валюта
STARS_CURRENCY = _env("STARS_CURRENCY", "⭐")
PRICE_STARS = _env_int("PRICE_STARS", 0)

# =========================
# Plans / Topups (монетизация)
# =========================
# Базовые планы (можешь потом менять цены/дни)
PLANS = {
    "START": {
        "title": "START",
        "days": _env_int("PLAN_START_DAYS", 30),
        "price_stars": _env_int("PLAN_START_PRICE", 299),
    },
    "PRO": {
        "title": "PRO",
        "days": _env_int("PLAN_PRO_DAYS", 30),
        "price_stars": _env_int("PLAN_PRO_PRICE", 599),
    },
    "ULTRA": {
        "title": "ULTRA",
        "days": _env_int("PLAN_ULTRA_DAYS", 30),
        "price_stars": _env_int("PLAN_ULTRA_PRICE", 999),
    },
}

# Пакеты докупки (если у тебя есть логика “докупить”)
TOPUPS = [
    {"code": "topup_100", "title": "100⭐", "stars": 100},
    {"code": "topup_300", "title": "300⭐", "stars": 300},
    {"code": "topup_500", "title": "500⭐", "stars": 500},
]

# =========================
# Referral / payouts (если используется db.py)
# =========================
REF_PERCENT = _env_float("REF_PERCENT", 0.10)  # 10%
MIN_PAYOUT_STARS = _env_int("MIN_PAYOUT_STARS", 1000)
PAYOUT_COOLDOWN_HOURS = _env_int("PAYOUT_COOLDOWN_HOURS", 72)
REF_REQUIRE_FIRST_PAYMENT = _env_bool("REF_REQUIRE_FIRST_PAYMENT", True)

REVENUE_DAYS_DEFAULT = _env_int("REVENUE_DAYS_DEFAULT", 30)

print("Config loaded")
print("TEXT_MODEL:", TEXT_MODEL)
print("IMAGE_MODEL:", IMAGE_MODEL)
print("MAX_TOKENS:", MAX_TOKENS)
