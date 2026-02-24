import os

# ======================
# TELEGRAM
# ======================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# ======================
# DATABASE
# ======================

DATABASE_URL = os.getenv("DATABASE_URL")

# ======================
# DEEPSEEK (TEXT + VISION)
# ======================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com"
)

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat"
)

DEEPSEEK_VISION_MODEL = os.getenv(
    "DEEPSEEK_VISION_MODEL",
    "deepseek-vision"
)

# ======================
# STABILITY (IMAGE GENERATION)
# ======================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

IMAGE_MODEL = os.getenv(
    "IMAGE_MODEL",
    "stable-diffusion-xl-1024-v1-0"
)

# ======================
# FALLBACK MODELS (если используются старые модули)
# ======================

TEXT_MODEL = os.getenv(
    "TEXT_MODEL",
    DEEPSEEK_MODEL
)

# ======================
# LIMITS
# ======================

FREE_TEXT_PER_DAY = int(
    os.getenv("FREE_TEXT_PER_DAY", "10")
)

FREE_IMG_PER_DAY = int(
    os.getenv("FREE_IMG_PER_DAY", "3")
)

# ======================
# SUBSCRIPTION
# ======================

PRICE_STARS = int(
    os.getenv("PRICE_STARS", "299")
)

STARS_CURRENCY = os.getenv(
    "STARS_CURRENCY",
    "XTR"
)

SUBSCRIBE_DAYS_DEFAULT = int(
    os.getenv("SUB_DAYS", "30")
)

# ======================
# DEBUG / INFO
# ======================

print("Config loaded")
print("DeepSeek model:", DEEPSEEK_MODEL)
print("Image model:", IMAGE_MODEL)
