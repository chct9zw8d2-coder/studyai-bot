\
import os

# Prefer TELEGRAM_BOT_TOKEN but allow BOT_TOKEN for convenience
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")

# Railway Postgres usually provides DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

