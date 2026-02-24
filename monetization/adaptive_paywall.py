
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def adaptive_offer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Активировать START (299⭐)", callback_data="menu:sub")],
        [InlineKeyboardButton("🔥 Активировать PRO (599⭐)", callback_data="menu:sub")],
    ])

def adaptive_offer_text():
    return (
        "Ты активно используешь StudyAI.\n\n"
        "С подпиской ты получишь больше решений, проверку фото и генерацию картинок.\n"
        "Это ускорит обучение в несколько раз."
    )
