from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from monetization.experiments import paywall_text_for_user

# Show a soft upsell after N free requests.
# PAYWALL_TRIGGER_COUNT is kept for backwards compatibility; prefer paywall_trigger_count_for_user()
PAYWALL_TRIGGER_COUNT = 5

def paywall_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Выбрать тариф", callback_data="menu:sub")],
    ])

def paywall_keyboard_full():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Полный разбор (подписка)", callback_data="menu:sub")],
    ])

def paywall_message_early():
    return (
        "✨ Похоже, бот тебе подходит.\n\n"
        "Чтобы учиться без ограничений, открой подписку:\n"
        "• START — 299⭐ / месяц\n"
        "• PRO — 599⭐ / месяц\n"
        "• ULTRA — 999⭐ / месяц\n\n"
        "Подписка даёт больше ответов, проверку фото ДЗ и генерацию картинок."
    )

def paywall_message_soft():
    return (
        "🔓 Ты используешь StudyAI бесплатно\n\n"
        "Подписка открывает:\n"
        "• больше ответов в день\n"
        "• проверку фото ДЗ\n"
        "• генерацию картинок\n"
        "• полный доступ к ОГЭ/ЕГЭ\n\n"
        "Выбери тариф START / PRO / ULTRA."
    )

def paywall_message_limit():
    return (
        "Ты использовал все бесплатные ответы на сегодня.\n\n"
        "Открой подписку и продолжай учиться без пауз."
    )


def paywall_message_soft_variant(user_id: int, winner: str | None = None):
    v, txt = paywall_text_for_user(user_id, winner=winner)
    return v, txt
def paywall_trigger_count_for_user(user_id: int) -> int:
    """
    Возвращает количество триггеров paywall для пользователя.
    Сейчас используется как заглушка (совместимость с bot.py).
    """
    return 0
