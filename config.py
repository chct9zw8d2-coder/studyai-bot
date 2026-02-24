# config.py
import os

def _env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return (v if v is not None else default).strip()

def _env_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = str(v).strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return default


# -------------------------
# REQUIRED (Railway Variables)
# -------------------------
TELEGRAM_BOT_TOKEN = _env_str("TELEGRAM_BOT_TOKEN")
DATABASE_URL = _env_str("DATABASE_URL")

OWNER_USER_ID = _env_int("OWNER_USER_ID", 0)
ADMIN_CHAT_ID = _env_int("ADMIN_CHAT_ID", 0)

DEEPSEEK_API_KEY = _env_str("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env_str("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Совместимость: кто-то кладёт модель в TEXT_MODEL, кто-то в DEEPSEEK_MODEL
DEEPSEEK_MODEL = _env_str("DEEPSEEK_MODEL") or _env_str("TEXT_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL = _env_str("DEEPSEEK_VISION_MODEL", "deepseek-vl")

# Для бесплатного режима можно использовать отдельную модель (если нет — берём основную)
DEEPSEEK_MODEL_FREE = _env_str("DEEPSEEK_MODEL_FREE", DEEPSEEK_MODEL)

STABILITY_API_KEY = _env_str("STABILITY_API_KEY")
# В логах у тебя ошибка именно на STABILITY_ENDPOINT — добавляем обязательно
STABILITY_ENDPOINT = _env_str("STABILITY_ENDPOINT", "https://api.stability.ai")


# -------------------------
# TOKENS / LIMITS
# -------------------------
# В логах у тебя была ошибка на MAX_TOKENS — добавляем обязательно
MAX_TOKENS = _env_int("MAX_TOKENS", 1000)

FREE_TEXT_PER_DAY = _env_int("FREE_TEXT_PER_DAY", _env_int("FREE_TEXT", 15))
FREE_IMG_PER_DAY = _env_int("FREE_IMG_PER_DAY", _env_int("FREE_IMG", 3))


# -------------------------
# STARS / PRICING
# -------------------------
# валюта Stars: обычно XTR
STARS_CURRENCY = _env_str("STARS_CURRENCY", "XTR")

# Совместимость с твоими переменными:
# PRICE_STARS (одна цена) / или дефолтные 299/599/999
PRICE_STARS = _env_int("PRICE_STARS", 299)

# Длительность подписки (если у тебя SUB_DAYS — используем её)
SUB_DAYS = _env_int("SUB_DAYS", 30)

# Пакеты пополнений (для “докупить”)
TOPUPS = [
    {"key": "topup_100", "title": "⭐ 100 Stars", "stars": 100},
    {"key": "topup_300", "title": "⭐ 300 Stars", "stars": 300},
    {"key": "topup_1000", "title": "⭐ 1000 Stars", "stars": 1000},
]

# Планы подписки (под это у тебя уже тексты в paywall)
PLANS = {
    "start": {
        "key": "start",
        "title": "START",
        "stars": _env_int("PLAN_START_STARS", 299),
        "days": _env_int("PLAN_START_DAYS", SUB_DAYS),
    },
    "pro": {
        "key": "pro",
        "title": "PRO",
        "stars": _env_int("PLAN_PRO_STARS", 599),
        "days": _env_int("PLAN_PRO_DAYS", SUB_DAYS),
    },
    "ultra": {
        "key": "ultra",
        "title": "ULTRA",
        "stars": _env_int("PLAN_ULTRA_STARS", 999),
        "days": _env_int("PLAN_ULTRA_DAYS", SUB_DAYS),
    },
}


# -------------------------
# REFERRALS / PAYOUT (нужно db.py)
# -------------------------
# db.py у тебя импортирует это:
REF_PERCENT = _env_int("REF_PERCENT", 20)                 # процент рефералки
MIN_PAYOUT_STARS = _env_int("MIN_PAYOUT_STARS", 100)      # минимальная сумма к выводу
PAYOUT_COOLDOWN_HOURS = _env_int("PAYOUT_COOLDOWN_HOURS", 24)
REF_REQUIRE_FIRST_PAYMENT = _env_bool("REF_REQUIRE_FIRST_PAYMENT", True)
REVENUE_DAYS_DEFAULT = _env_int("REVENUE_DAYS_DEFAULT", 30)


# -------------------------
# CACHE (если в bot.py включено)
# -------------------------
ENABLE_TEXT_CACHE = _env_bool("ENABLE_TEXT_CACHE", True)
ENABLE_IMAGE_CACHE = _env_bool("ENABLE_IMAGE_CACHE", True)
TEXT_CACHE_TTL_DAYS = _env_int("TEXT_CACHE_TTL_DAYS", 7)
IMAGE_CACHE_TTL_DAYS = _env_int("IMAGE_CACHE_TTL_DAYS", 7)


# -------------------------
# IMAGE MODEL (для логов/совместимости)
# -------------------------
# В Railway у тебя есть IMAGE_MODEL / TEXT_MODEL — оставим оба сценария
IMAGE_MODEL = _env_str("IMAGE_MODEL", "flux")

# Небольшой лог при старте (не критично)
if __name__ == "__main__":
    print("Config loaded")
    print("DEEPSEEK_MODEL:", DEEPSEEK_MODEL)
    print("DEEPSEEK_VISION_MODEL:", DEEPSEEK_VISION_MODEL)
    print("IMAGE_MODEL:", IMAGE_MODEL)
    print("MAX_TOKENS:", MAX_TOKENS)
