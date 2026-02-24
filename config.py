import os

# ======================
# ОСНОВНЫЕ НАСТРОЙКИ
# ======================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

TEXT_MODEL = os.getenv("TEXT_MODEL", "deepseek-chat")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "flux")

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "10"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "3"))

SUBSCRIBE_DAYS_DEFAULT = int(os.getenv("SUB_DAYS", "30"))

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))

PRICE_STARS = int(os.getenv("PRICE_STARS", "299"))
STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

# ======================
# ПОДПИСКИ
# ======================

PLANS = {
    "START": {
        "price": 299,
        "days": 30,
        "text_per_day": 50,
        "img_per_day": 10,
    },
    "PRO": {
        "price": 599,
        "days": 30,
        "text_per_day": 200,
        "img_per_day": 50,
    },
    "ULTRA": {
        "price": 999,
        "days": 30,
        "text_per_day": 1000,
        "img_per_day": 200,
    },
}

# ======================
# РЕФЕРАЛКА
# ======================

REF_PERCENT = 0.20
MIN_PAYOUT_STARS = 100
PAYOUT_COOLDOWN_HOURS = 24
REF_REQUIRE_FIRST_PAYMENT = True

# ======================
# ДОНАТЫ / ТОПАПЫ
# ======================

TOPUPS = {
    "50": 50,
    "100": 100,
    "250": 250,
    "500": 500,
    "1000": 1000,
}

print("Config loaded")
print("DeepSeek model:", TEXT_MODEL)
print("Image model:", IMAGE_MODEL)
