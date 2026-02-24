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
TEXT_CACHE_TTL_DAYS = int(os.getenv("TEXT_CACHE_TTL_DAYS", "60"))


# Telegram Stars
STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

# Pricing: tuned for high fees (Stars platform fee + top-up commissions on AI credits).
# daily_img теперь используется как лимит "фото-разборов" (проверка ДЗ по фото).
PLANS = {
    "free":  {"name": {"ru": "FREE", "en": "FREE"},       "price_stars": 0,    "daily_text": 20,   "daily_img": 1},
    "start": {"name": {"ru": "START", "en": "START"},     "price_stars": 149,  "daily_text": 120,  "daily_img": 10},
    "start_first": {"name": {"ru": "START −20% (первый месяц)", "en": "START −20% (first month)"}, "price_stars": 119, "daily_text": 120, "daily_img": 10},
    "pro":   {"name": {"ru": "PRO", "en": "PRO"},         "price_stars": 299,  "daily_text": 400,  "daily_img": 30},
    "ultra": {"name": {"ru": "ULTRA", "en": "ULTRA"},     "price_stars": 499,  "daily_text": 1200, "daily_img": 100},
}


TOPUPS = {
    # 🔥 Weekly deal (best conversion in RU)
    "week_pack": {"title": {"ru": "🔥 Пакет недели: +250 ответов", "en": "🔥 Weekly pack: +250 answers"}, "stars": 249, "add_text": 250, "add_img": 0},

    # Text answers top-ups
    "text_50":   {"title": {"ru": "Докупить +50 ответов",  "en": "Top up +50 answers"},  "stars": 75,  "add_text": 50,  "add_img": 0},
    "text_200":  {"title": {"ru": "Докупить +200 ответов", "en": "Top up +200 answers"}, "stars": 199, "add_text": 200, "add_img": 0},

    # 📸 Photo checks top-ups (homework photos / grading by photo)
    "img_10":    {"title": {"ru": "📸 Докупить +10 фото-разборов",  "en": "📸 Top up +10 photo checks"},  "stars": 99,  "add_text": 0, "add_img": 10},
    "img_50":    {"title": {"ru": "📸 Докупить +50 фото-разборов",  "en": "📸 Top up +50 photo checks"},  "stars": 299, "add_text": 0, "add_img": 50},
    "img_200":   {"title": {"ru": "📸 Докупить +200 фото-разборов", "en": "📸 Top up +200 photo checks"}, "stars": 799, "add_text": 0, "add_img": 200},
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

REVENUE_DAYS_DEFAULT = int(os.getenv("REVENUE_DAYS_DEFAULT", "7"))


