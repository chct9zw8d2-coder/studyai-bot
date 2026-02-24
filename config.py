import os

# =========================
# ОСНОВНЫЕ НАСТРОЙКИ
# =========================

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Админ
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))

# База данных
DATABASE_URL = os.getenv("DATABASE_URL", "")


# =========================
# DeepSeek (текст)
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat"
)

DEEPSEEK_VISION_MODEL = os.getenv(
    "DEEPSEEK_VISION_MODEL",
    "deepseek-chat"
)


# =========================
# Stability AI (картинки)
# =========================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# ВАЖНО: именно этого не хватало
STABILITY_ENDPOINT = "https://api.stability.ai"

IMAGE_MODEL = os.getenv(
    "IMAGE_MODEL",
    "stable-image-ultra"
)


# =========================
# ЛИМИТЫ FREE
# =========================

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "10"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "3"))


# =========================
# ПОДПИСКИ
# =========================

SUB_DAYS = int(os.getenv("SUB_DAYS", "30"))

PLANS = {
    "start": {
        "name": "START",
        "price": 299,
        "stars": 299,
        "days": 30
    },
    "pro": {
        "name": "PRO",
        "price": 599,
        "stars": 599,
        "days": 30
    },
    "ultra": {
        "name": "ULTRA",
        "price": 999,
        "stars": 999,
        "days": 30
    }
}

PRICE_STARS = {
    "start": 299,
    "pro": 599,
    "ultra": 999
}

STARS_CURRENCY = "XTR"


# =========================
# РЕФЕРАЛКА
# =========================

REF_PERCENT = 0.20
MIN_PAYOUT_STARS = 100
PAYOUT_COOLDOWN_HOURS = 24
REF_REQUIRE_FIRST_PAYMENT = True


# =========================
# ТОПАПЫ
# =========================

TOPUPS = {
    "small": 100,
    "medium": 500,
    "large": 1000
}


# =========================
# PAYWALL
# =========================

SUBSCRIBE_DAYS_DEFAULT = 30


# =========================
# LOG
# =========================

print("Config loaded")
print("DeepSeek model:", DEEPSEEK_MODEL)
print("Image model:", IMAGE_MODEL)
