import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0")) or OWNER_USER_ID

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# DeepSeek (optional cheaper model for FREE to reduce costs)
DEEPSEEK_MODEL_FREE = os.getenv("DEEPSEEK_MODEL_FREE", DEEPSEEK_MODEL)

# Token caps per plan (reduces cost for FREE)
MAX_TOKENS = {
    "free": 600,
    "start": 900,
    "pro": 1400,
    "ultra": 2200,
}

# Cache settings (saves money)
ENABLE_TEXT_CACHE = os.getenv("ENABLE_TEXT_CACHE", "1") == "1"
ENABLE_IMAGE_CACHE = os.getenv("ENABLE_IMAGE_CACHE", "1") == "1"
TEXT_CACHE_TTL_DAYS = int(os.getenv("TEXT_CACHE_TTL_DAYS", "60"))
IMAGE_CACHE_TTL_DAYS = int(os.getenv("IMAGE_CACHE_TTL_DAYS", "180"))


# Telegram Stars
STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

# Pricing: tuned for high fees (Stars platform fee + top-up commissions on AI credits).
# FREE keeps image generation disabled by default (daily_img: 0) to prevent cost leaks.
PLANS = {
    "free":  {"name": {"ru": "FREE", "en": "FREE"},       "price_stars": 0,    "daily_text": 20,   "daily_img": 0},
    "start": {"name": {"ru": "START", "en": "START"},     "price_stars": 299,  "daily_text": 120,  "daily_img": 3},
    "start_first": {"name": {"ru": "START −20% (первый месяц)", "en": "START −20% (first month)"}, "price_stars": 239, "daily_text": 120, "daily_img": 3},
    "pro":   {"name": {"ru": "PRO", "en": "PRO"},         "price_stars": 599,  "daily_text": 400,  "daily_img": 10},
    "ultra": {"name": {"ru": "ULTRA", "en": "ULTRA"},     "price_stars": 999,  "daily_text": 1200, "daily_img": 30},
}


TOPUPS = {
    # 🔥 Weekly deal (best conversion in RU)
    "week_pack": {"title": {"ru": "🔥 Пакет недели: +250 ответов и +8 картинок", "en": "🔥 Weekly pack: +250 answers and +8 images"}, "stars": 499, "add_text": 250, "add_img": 8},

    "text_50":   {"title": {"ru": "Докупить +50 ответов",  "en": "Top up +50 answers"},  "stars": 149, "add_text": 50,  "add_img": 0},
    "text_200":  {"title": {"ru": "Докупить +200 ответов", "en": "Top up +200 answers"}, "stars": 399, "add_text": 200, "add_img": 0},
    "img_5":     {"title": {"ru": "Докупить +5 картинок",  "en": "Top up +5 images"},    "stars": 249, "add_text": 0,   "add_img": 5},
    "img_15":    {"title": {"ru": "Докупить +15 картинок", "en": "Top up +15 images"},   "stars": 599, "add_text": 0,   "add_img": 15},
}


REF_PERCENT = float(os.getenv("REF_PERCENT", "0.30"))
MIN_PAYOUT_STARS = int(os.getenv("MIN_PAYOUT_STARS", "300"))
PAYOUT_COOLDOWN_HOURS = int(os.getenv("PAYOUT_COOLDOWN_HOURS", "24"))
REF_REQUIRE_FIRST_PAYMENT = os.getenv("REF_REQUIRE_FIRST_PAYMENT", "1") in ("1","true","True","yes","Y")

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "12"))

# Anti-abuse / cost control
RATE_LIMIT_TEXT_PER_MIN = int(os.getenv("RATE_LIMIT_TEXT_PER_MIN", "18"))
RATE_LIMIT_IMAGE_PER_MIN = int(os.getenv("RATE_LIMIT_IMAGE_PER_MIN", "4"))
DUPLICATE_WINDOW_SEC = int(os.getenv("DUPLICATE_WINDOW_SEC", "30"))
DUPLICATE_MAX = int(os.getenv("DUPLICATE_MAX", "3"))

# Two-level answers: FREE gets concise answers; paid can request full breakdown
ENABLE_TWO_LEVEL_ANSWERS = os.getenv("ENABLE_TWO_LEVEL_ANSWERS", "1") == "1"
EARLY_PAYWALL_TRIGGER_COUNT = int(os.getenv("EARLY_PAYWALL_TRIGGER_COUNT", "2"))
MAX_TEXT_LEN = int(os.getenv("MAX_TEXT_LEN", "4000"))

# Stability AI (IMAGES ONLY)
# Default endpoint points to Stable Image Generate (SD3 route). If your account uses another route, set STABILITY_ENDPOINT.
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
STABILITY_ENDPOINT = os.getenv("STABILITY_ENDPOINT", "https://api.stability.ai/v2beta/stable-image/generate/sd3")
STABILITY_OUTPUT_FORMAT = os.getenv("STABILITY_OUTPUT_FORMAT", "png")

REVENUE_DAYS_DEFAULT = int(os.getenv("REVENUE_DAYS_DEFAULT", "7"))


# =========================
# OPTIMAL TARIFFS FOR RUSSIA
# =========================

SUBSCRIPTION_PLANS = {
    "START": {
        "price_stars": 299,
        "duration_days": 30,
        "limits": {
            "text_per_day": 120,
            "image_per_day": 3,
        }
    },
    "PRO": {
        "price_stars": 599,
        "duration_days": 30,
        "limits": {
            "text_per_day": 400,
            "image_per_day": 10,
        }
    },
    "ULTRA": {
        "price_stars": 999,
        "duration_days": 30,
        "limits": {
            "text_per_day": 1200,
            "image_per_day": 30,
        }
    }
}

TOPUP_PACKAGES = {
    "text_small": {"stars": 149, "text": 50},
    "text_big": {"stars": 399, "text": 200},
    "image_small": {"stars": 249, "image": 5},
    "image_big": {"stars": 599, "image": 15},
}
