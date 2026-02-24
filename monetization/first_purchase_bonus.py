from telegram import InlineKeyboardMarkup, InlineKeyboardButton

BONUS_TEXT = 150


def bonus_offer_text(variant: str = "bonus_text") -> str:
    """Text-only first purchase bonus.

    We keep the `variant` parameter for backward compatibility with existing A/B logic,
    but it is ignored now because image generation was removed.
    """
    return (
        "🎁 Бонус за первую покупку!\n\n"
        f"Подключи START и получи сегодня +{BONUS_TEXT} ответов бесплатно."
    )


def bonus_offer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Выбрать тариф", callback_data="menu:sub")],
    ])


def bonus_payload(variant: str = "bonus_text") -> dict:
    return {"add_text": BONUS_TEXT, "add_img": 0}
