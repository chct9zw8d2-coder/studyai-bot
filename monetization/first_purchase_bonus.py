from telegram import InlineKeyboardMarkup, InlineKeyboardButton

BONUS_TEXT = 150
BONUS_IMG = 3

def bonus_offer_text(variant: str) -> str:
    if variant == "bonus_img":
        return (
            "🎁 Бонус за первую покупку!\n\n"
            f"Подключи START и получи сегодня +{BONUS_IMG} картинок бесплатно."
        )
    # default: bonus_text
    return (
        "🎁 Бонус за первую покупку!\n\n"
        f"Подключи START и получи сегодня +{BONUS_TEXT} ответов бесплатно."
    )

def bonus_offer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Подключить START (299⭐)", callback_data="menu:sub")],
    ])

def bonus_payload(variant: str) -> dict:
    if variant == "bonus_img":
        return {"add_text": 0, "add_img": BONUS_IMG}
    return {"add_text": BONUS_TEXT, "add_img": 0}
