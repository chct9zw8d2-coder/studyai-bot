import os

# =========================
# TELEGRAM
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))

# =========================
# DATABASE
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# DEEPSEEK
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

TEXT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-chat")

# =========================
# STABILITY IMAGE
# =========================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "flux")

# =========================
# FREE LIMITS
# =========================

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "10"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "3"))

# =========================
# SUBSCRIPTION SETTINGS
# =========================

SUBSCRIBE_DAYS_DEFAULT = int(os.getenv("SUB_DAYS", "30"))

STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

PRICE_STARS = int(os.getenv("PRICE_STARS", "99"))

# =========================
# PLANS (ОБЯЗАТЕЛЬНО для db.py)
# =========================

PLANS = {
    "START": {
        "stars": 99,
        "days": 30,
        "text_per_day": 100,
        "img_per_day": 20,
    },
    "PRO": {
        "stars": 299,
        "days": 30,
        "text_per_day": 500,
        "img_per_day": 100,
    },
    "ULTRA": {
        "stars": 599,
        "days": 30,
        "text_per_day": 2000,
        "img_per_day": 500,
    }
}

# =========================
# REFERRAL SYSTEM
# =========================

REF_PERCENT = 20

MIN_PAYOUT_STARS = 500

PAYOUT_COOLDOWN_HOURS = 24

REF_REQUIRE_FIRST_PAYMENT = True

# =========================
# STARTUP LOG
# =========================

print("Config loaded")
print("DeepSeek model:", TEXT_MODEL)
print("Image model:", IMAGE_MODEL)
