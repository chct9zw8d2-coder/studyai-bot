import os

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CURRENCY = "XTR"  # Telegram Stars
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "")  # For Stars обычно можно оставить пустым

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Optional: Replicate for music (later)
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# Limits per day (free baseline)
FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "5"))
FREE_IMG_PER_DAY  = int(os.getenv("FREE_IMG_PER_DAY", "2"))

SUB_DAYS = int(os.getenv("SUB_DAYS", "30"))

PLANS = {
    "free":   {"name": "Free",   "price": 0,   "text_per_day": FREE_TEXT_PER_DAY, "img_per_day": FREE_IMG_PER_DAY},
    "basic":  {"name": "Basic",  "price": 199, "text_per_day": 50,  "img_per_day": 10},
    "pro":    {"name": "Pro",    "price": 499, "text_per_day": 200, "img_per_day": 50},
    "ultra":  {"name": "Ultra",  "price": 999, "text_per_day": 500, "img_per_day": 120},
}

# One-off purchases (Stars)
TOPUPS = {
    "text_25": {"name": "Докупить 25 текстов", "price": 79, "amount": 25, "kind": "text"},
    "img_5":   {"name": "Докупить 5 картинок", "price": 99, "amount": 5,  "kind": "img"},
    "song_1":  {"name": "Песня/музыка (1)",    "price": 150,"amount": 1,  "kind": "song"},
}
