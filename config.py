import os

# =========================
# BASIC
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))

# =========================
# DEEPSEEK
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-chat")

TEXT_MODEL = DEEPSEEK_MODEL

# =========================
# STABILITY (images)
# =========================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "flux")

# =========================
# FREE LIMITS
# =========================

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "5"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "2"))

# =========================
# SUBSCRIPTION
# =========================

SUB_DAYS = int(os.getenv("SUB_DAYS", "30"))
SUBSCRIBE_DAYS_DEFAULT = SUB_DAYS

STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")
PRICE_STARS = int(os.getenv("PRICE_STARS", "199"))

# =========================
# PLANS (ВАЖНО — это исправляет ошибку)
# =========================

PLANS = {
    "START": {
        "name": "START",
        "price_stars": 199,
        "days": 30,
        "text_per_day": 50,
        "img_per_day": 10
    },
    "PRO": {
        "name": "PRO",
        "price_stars": 399,
        "days": 30,
        "text_per_day": 200,
        "img_per_day": 50
    },
    "ULTRA": {
        "name": "ULTRA",
        "price_stars": 799,
        "days": 30,
        "text_per_day": 9999,
        "img_per_day": 9999
    }
}

# =========================
# REFERRAL SYSTEM
# =========================

REF_PERCENT = 20
MIN_PAYOUT_STARS = 1000
PAYOUT_COOLDOWN_HOURS = 24
REF_REQUIRE_FIRST_PAYMENT = True

# =========================
# PAYWALL
# =========================

PAYWALL_TRIGGER_COUNT = 3

# =========================
# LOG
# =========================

print("Config loaded")
print("DeepSeek model:", DEEPSEEK_MODEL)
print("Image model:", IMAGE_MODEL)
