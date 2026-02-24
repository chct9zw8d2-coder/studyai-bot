
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import datetime as dt

from monetization.ab_test import choose_variant

# Experiments registry
# NOTE: Variants are stable by user_id (hash bucket). Winners (if any) are applied globally via db.

START_PRICE_VARIANTS = {
    "p299": 299,
    "p349": 349,
    "p399": 399,
}

PAYWALL_TEXT_VARIANTS = {
    "a": "🔓 Ты используешь StudyAI бесплатно. Открой подписку, чтобы получать больше решений и проверять фото ДЗ.",
    "b": "🎓 С подпиской ты будешь учиться быстрее: больше решений, разборы, фото‑проверка и картинки.",
    "c": "⚡ Уже многие ученики учатся с StudyAI. Открой подписку, чтобы снять лимиты и получить полный доступ.",
}

WEEK_DEAL_VARIANTS = {
    "combo": {"stars": 499, "add_text": 250, "add_img": 8,  "title": {"ru": "🔥 Пакет недели: +250 ответов и +8 картинок", "en": "🔥 Weekly pack: +250 answers and +8 images"}},
    "text":  {"stars": 399, "add_text": 350, "add_img": 0,  "title": {"ru": "🔥 Пакет недели: +350 ответов", "en": "🔥 Weekly pack: +350 answers"}},
    "img":   {"stars": 599, "add_text": 0,   "add_img": 12, "title": {"ru": "🔥 Пакет недели: +12 картинок", "en": "🔥 Weekly pack: +12 images"}},
    "ultra": {"stars": 799, "add_text": 500, "add_img": 15, "title": {"ru": "🔥 Пакет недели ULTRA: +500 ответов и +15 картинок", "en": "🔥 Weekly ULTRA pack: +500 answers and +15 images"}},
}

def pick_variant(user_id: int, experiment: str, variants: List[str], winner: Optional[str] = None) -> str:
    # If a winner is set globally, use it; otherwise stable per-user assignment.
    if winner and winner in variants:
        return winner
    return choose_variant(user_id, experiment, variants)

def start_price_for_user(user_id: int, winner: Optional[str] = None) -> tuple[str,int]:
    v = pick_variant(user_id, "start_price", list(START_PRICE_VARIANTS.keys()), winner=winner)
    return v, START_PRICE_VARIANTS[v]

def paywall_text_for_user(user_id: int, winner: Optional[str] = None) -> tuple[str,str]:
    v = pick_variant(user_id, "paywall_text", list(PAYWALL_TEXT_VARIANTS.keys()), winner=winner)
    return v, PAYWALL_TEXT_VARIANTS[v]

def week_deal_for_user(user_id: int, winner: Optional[str] = None) -> tuple[str, Dict[str,Any]]:
    v = pick_variant(user_id, "week_deal", list(WEEK_DEAL_VARIANTS.keys()), winner=winner)
    return v, WEEK_DEAL_VARIANTS[v]


# Recommend plan experiment (what to highlight as "recommended" in UI)
RECOMMEND_PLAN_VARIANTS = {
    "rec_start": "start",
    "rec_pro": "pro",
}

# Paywall trigger experiment (after how many free answers show soft paywall)
PAYWALL_TRIGGER_VARIANTS = {
    "t2": 2,
    "t5": 5,
}

def recommend_plan_for_user(user_id: int, winner: Optional[str] = None) -> tuple[str,str]:
    v = pick_variant(user_id, "recommend_plan", list(RECOMMEND_PLAN_VARIANTS.keys()), winner=winner)
    return v, RECOMMEND_PLAN_VARIANTS[v]

def paywall_trigger_for_user(user_id: int, winner: Optional[str] = None) -> tuple[str,int]:
    v = pick_variant(user_id, "paywall_trigger", list(PAYWALL_TRIGGER_VARIANTS.keys()), winner=winner)
    return v, PAYWALL_TRIGGER_VARIANTS[v]
