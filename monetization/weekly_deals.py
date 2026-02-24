from monetization.experiments import week_deal_for_user


def get_week_deal_for(uid: int, winner: str | None = None):
    """Return (variant, deal_dict)"""
    return week_deal_for_user(uid, winner=winner)

import datetime as dt

DEALS = [
    {
        "kind": "combo",
        "stars": 499,
        "add_text": 250,
        "add_img": 8,
        "title": {
            "ru": "🔥 Пакет недели (Комбо): +250 ответов и +8 картинок",
            "en": "🔥 Weekly pack (Combo): +250 answers and +8 images",
        },
    },
    {
        "kind": "answers",
        "stars": 399,
        "add_text": 350,
        "add_img": 0,
        "title": {
            "ru": "🔥 Пакет недели (Ответы): +350 ответов",
            "en": "🔥 Weekly pack (Answers): +350 answers",
        },
    },
    {
        "kind": "images",
        "stars": 599,
        "add_text": 0,
        "add_img": 12,
        "title": {
            "ru": "🔥 Пакет недели (Картинки): +12 картинок",
            "en": "🔥 Weekly pack (Images): +12 images",
        },
    },
]

def get_week_deal(today: dt.date | None = None) -> dict:
    if today is None:
        today = dt.datetime.utcnow().date()
    week = today.isocalendar().week
    return DEALS[week % len(DEALS)].copy()
