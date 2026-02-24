import os

# =========================
# TELEGRAM
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# =========================
# DATABASE
# =========================

DATABASE_URL = os.getenv("DATABASE_URL", "")

# =========================
# DEEPSEEK
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-chat")

TEXT_MODEL = DEEPSEEK_MODEL

# =========================
# STABILITY AI (ВАЖНО)
# =========================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# ЭТО НУЖНО ДОБАВИТЬ
STABILITY_ENDPOINT = "https://api.stability.ai"

IMAGE_MODEL = os.getenv("IMAGE_MODEL", "stable-image-ultra")

# =========================
# LIMITS
# =========================

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "10"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "3"))

# =========================
# SUBSCRIPTION
# =========================

SUBSCRIBE_DAYS_DEFAULT = int(os.getenv("SUB_DAYS", "30"))

STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

PRICE_STARS = int(os.getenv("PRICE_STARS", "299"))

PLANS = {
    "START": {
        "name": "START",
        "price_stars": 299,
        "days": 30,
        "text_per_day": 50,
        "img_per_day": 10
    },
    "PRO": {
        "name": "PRO",
        "price_stars": 599,
        "days": 30,
        "text_per_day": 200,
        "img_per_day": 50
    },
    "ULTRA": {
        "name": "ULTRA",
        "price_stars": 999,
        "days": 30,
        "text_per_day": 9999,
        "img_per_day": 9999
    }
}

# =========================
# TOPUPS
# =========================

TOPUPS = {
    "img_10": 10,
    "img_50": 50,
    "img_100": 100
}

# =========================
# REFERRAL SYSTEM
# =========================

REF_PERCENT = 20
MIN_PAYOUT_STARS = 1000
PAYOUT_COOLDOWN_HOURS = 24
REF_REQUIRE_FIRST_PAYMENT = True

# =========================
# LOG
# =========================

print("Config loaded")
print("DeepSeek model:", DEEPSEEK_MODEL)
print("Image model:", IMAGE_MODEL)
