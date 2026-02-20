import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

STARS_CURRENCY = os.getenv("STARS_CURRENCY", "XTR")

PLANS = {
    "free":  {"name": {"ru": "FREE", "en": "FREE"},  "price_stars": 0,   "daily_text": 3,   "daily_img": 1,  "daily_song": 0},
    "pro":   {"name": {"ru": "PRO", "en": "PRO"},    "price_stars": 499, "daily_text": 80,  "daily_img": 15, "daily_song": 1},
    "ultra": {"name": {"ru": "ULTRA", "en": "ULTRA"},"price_stars": 999, "daily_text": 250, "daily_img": 50, "daily_song": 5},
}

TOPUPS = {
    "text_50": {"title": {"ru": "Докупить +50 ответов", "en": "Top up +50 answers"}, "price_stars": 149, "add_text": 50, "requires_sub": True},
    "img_10":  {"title": {"ru": "Докупить +10 картинок", "en": "Top up +10 images"}, "price_stars": 199, "add_img": 10, "requires_sub": True},
    "song_1":  {"title": {"ru": "1 трек (музыка)", "en": "1 track (music)"}, "price_stars": 150, "add_song": 1, "requires_sub": False},
}

REF_BONUS_INVITER = {"add_text": 20, "add_img": 3, "add_song": 1}
REF_BONUS_INVITEE = {"add_text": 10, "add_img": 1, "add_song": 0}

MUSIC_SECONDS = int(os.getenv("MUSIC_SECONDS", "30"))
