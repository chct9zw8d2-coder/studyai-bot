
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CURRENCY = "XTR"

FREE_TEXT_PER_DAY = int(os.getenv("FREE_TEXT_PER_DAY", "5"))
FREE_IMG_PER_DAY = int(os.getenv("FREE_IMG_PER_DAY", "3"))

PLANS = {
    "basic": {"name": "Basic", "price": 199, "text_per_day": 50, "img_per_day": 15, "topup_price": 40, "topup_text": 50, "topup_img": 15},
    "pro":   {"name": "Pro",   "price": 499, "text_per_day": 200, "img_per_day": 60, "topup_price": 100, "topup_text": 200, "topup_img": 60},
    "ultra": {"name": "Ultra", "price": 999, "text_per_day": 500, "img_per_day": 150, "topup_price": 180, "topup_text": 500, "topup_img": 150},
}
SUB_DAYS = int(os.getenv("SUB_DAYS", "30"))

SONG_PRICE = int(os.getenv("SONG_PRICE", "150"))
SONG_DURATION = int(os.getenv("SONG_DURATION", "12"))
