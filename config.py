import os

# ======================
# TELEGRAM
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# ======================
# DATABASE
# ======================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

# ======================
# AI MODELS
# ======================

TEXT_MODEL = os.getenv("TEXT_MODEL", "deepseek-chat")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "flux")

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))

# ======================
# STABILITY AI
# ======================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
STABILITY_ENDPOINT = "https://api.stability.ai"

# ======================
# PAYWALL / SUBSCRIPTIONS
# ======================

SUBSCRIBE_DAYS_DEFAULT = 30

PLANS = {
    "start": {
        "name": "START",
        "price": 299,
        "days": 30,
        "daily_limit": 20
    },
    "pro": {
        "name": "PRO",
        "price": 599,
        "days": 30,
        "daily_limit": 100
    },
    "ultra": {
        "name": "ULTRA",
        "price": 999,
        "days": 30,
        "daily_limit": 1000
    }
}

# ======================
# TOPUPS (докупка лимитов)
# ======================

TOPUPS = {
    "small": {
        "price": 99,
        "credits": 50
    },
    "medium": {
        "price": 199,
        "credits": 150
    },
    "large": {
        "price": 399,
        "credits": 400
    }
}

# ======================
# REFERRAL SYSTEM
# ======================

REF_PERCENT = 0.30
MIN_PAYOUT_STARS = 100
PAYOUT_COOLDOWN_HOURS = 24
REF_REQUIRE_FIRST_PAYMENT = True

# ======================
# DEBUG
# ======================

print("Config loaded")
print("TEXT_MODEL:", TEXT_MODEL)
print("IMAGE_MODEL:", IMAGE_MODEL)
print("MAX_TOKENS:", MAX_TOKENS)
