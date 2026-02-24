from monetization.experiments import week_deal_for_user


def get_week_deal_for(uid: int, winner: str | None = None):
    """Return (variant, deal_dict)"""
    return week_deal_for_user(uid, winner=winner)

import datetime as dt

DEALS = [
    {
        "kind": "answers",
        "stars": 249,
        "add_text": 250,
        "add_img": 0,
        "title": {"ru": "🔥 Пакет недели: +250 ответов", "en": "🔥 Weekly pack: +250 answers"},
    },
]


def get_week_deal(today: dt.date | None = None) -> dict:
    if today is None:
        today = dt.datetime.utcnow().date()
    week = today.isocalendar().week
    return DEALS[week % len(DEALS)].copy()
