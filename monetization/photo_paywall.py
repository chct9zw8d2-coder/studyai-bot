
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def photo_paywall_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Открыть START (299⭐)", callback_data="menu:sub")]
    ])

def photo_paywall_text():
    return (
        "📷 Проверка фото ДЗ доступна с тарифом START и выше.\n\n"
        "Это позволяет:\n"
        "• точно распознавать задания\n"
        "• давать подробный разбор\n"
        "• обучать быстрее\n\n"
        "Открой START, чтобы продолжить."
    )
