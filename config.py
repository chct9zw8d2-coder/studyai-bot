import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Plan:
    name: str
    price_stars: int
    text_per_day: int
    img_per_day: int
    topup_price_stars: int
    topup_text: int
    topup_img: int

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_url: str

    # AI
    text_model: str = "openai"
    image_model: str = "flux"
    request_timeout_sec: int = 90
    max_prompt_len: int = 2000

    # Subscription
    sub_days: int = 30
    renew_reminder_days: int = 2  # remind N days before expiration

    # Free limits (per UTC day)
    free_text_per_day: int = 5
    free_img_per_day: int = 3

    # Paid plans (per UTC day)
    plan_basic: Plan = Plan("Basic", 199, 50, 15, 40, 50, 15)
    plan_pro: Plan = Plan("Pro", 499, 200, 60, 100, 200, 60)
    plan_ultra: Plan = Plan("Ultra", 999, 500, 150, 180, 500, 150)

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip() or default)
    except Exception:
        return default

def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN. Добавь его в Variables (Railway) или .env (локально).")

    db = os.getenv("DATABASE_URL", "").strip()
    if not db:
        raise RuntimeError("Не найден DATABASE_URL. На Railway добавь PostgreSQL и прокинь DATABASE_URL в Variables сервиса бота.")

    # Plans can be overridden via env if needed
    basic = Plan(
        "Basic",
        _int("BASIC_PRICE_STARS", 199),
        _int("BASIC_TEXT_PER_DAY", 50),
        _int("BASIC_IMG_PER_DAY", 15),
        _int("BASIC_TOPUP_PRICE_STARS", 40),
        _int("BASIC_TOPUP_TEXT", 50),
        _int("BASIC_TOPUP_IMG", 15),
    )
    pro = Plan(
        "Pro",
        _int("PRO_PRICE_STARS", 499),
        _int("PRO_TEXT_PER_DAY", 200),
        _int("PRO_IMG_PER_DAY", 60),
        _int("PRO_TOPUP_PRICE_STARS", 100),
        _int("PRO_TOPUP_TEXT", 200),
        _int("PRO_TOPUP_IMG", 60),
    )
    ultra = Plan(
        "Ultra",
        _int("ULTRA_PRICE_STARS", 999),
        _int("ULTRA_TEXT_PER_DAY", 500),
        _int("ULTRA_IMG_PER_DAY", 150),
        _int("ULTRA_TOPUP_PRICE_STARS", 180),
        _int("ULTRA_TOPUP_TEXT", 500),
        _int("ULTRA_TOPUP_IMG", 150),
    )

    return Settings(
        telegram_bot_token=token,
        database_url=db,
        text_model=(os.getenv("TEXT_MODEL", "openai").strip() or "openai"),
        image_model=(os.getenv("IMAGE_MODEL", "flux").strip() or "flux"),
        request_timeout_sec=_int("REQUEST_TIMEOUT_SEC", 90),
        max_prompt_len=_int("MAX_PROMPT_LEN", 2000),
        sub_days=_int("SUB_DAYS", 30),
        renew_reminder_days=_int("RENEW_REMINDER_DAYS", 2),
        free_text_per_day=_int("FREE_TEXT_PER_DAY", 5),
        free_img_per_day=_int("FREE_IMG_PER_DAY", 3),
        plan_basic=basic,
        plan_pro=pro,
        plan_ultra=ultra,
    )
