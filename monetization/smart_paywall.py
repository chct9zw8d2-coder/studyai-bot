# monetization/smart_paywall.py
"""
Smart paywall helpers (Telegram Stars monetization).

This module is intentionally "compatibility-safe":
- bot.py can import:
  PAYWALL_TRIGGER_COUNT,
  paywall_keyboard,
  paywall_keyboard_full,
  paywall_message_early,
  paywall_message_soft,
  paywall_message_limit,
  paywall_trigger_count_for_user

It also provides:
- photo_paywall_* helpers (optional) for "photo quota ended" flows.

If some config fields are missing, module will still load (fallback text).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
except Exception:  # pragma: no cover
    InlineKeyboardButton = object  # type: ignore
    InlineKeyboardMarkup = object  # type: ignore


# ---- Config safe imports ----
def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
        return default


try:
    import config  # type: ignore
except Exception:  # pragma: no cover
    config = None  # type: ignore


# ---- Public constant expected by bot.py ----
# How many paywall triggers before we switch from soft to harder messaging (used by some flows).
PAYWALL_TRIGGER_COUNT = 2


# ---- Helpers ----
def _mk_btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)  # type: ignore


def _mk_kb(rows: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)  # type: ignore


def _plans() -> Dict[str, Any]:
    """
    Expected shape in config:
      PLANS = {
        "START": {"price_stars": 149, ...},
        "PRO":   {"price_stars": 299, ...},
        "ULTRA": {"price_stars": 499, ...},
        ...
      }
    """
    if config is None:
        return {}
    return getattr(config, "PLANS", {}) or {}


def _topups() -> Dict[str, Any]:
    """
    Expected shape in config:
      TOPUPS = {
        "text_50":  {"title": "+50 ответов", "price_stars": 75,  "add_text": 50},
        "photo_10": {"title": "+10 фото-разборов", "price_stars": 99, "add_photo": 10},
        ...
      }
    """
    if config is None:
        return {}
    return getattr(config, "TOPUPS", {}) or {}


def _fmt_stars(n: Any) -> str:
    try:
        return f"{int(n)}⭐"
    except Exception:
        return "⭐"


def _sorted_plans_for_buttons() -> List[Tuple[str, Dict[str, Any]]]:
    plans = _plans()
    # Prefer this order if keys exist
    order = ["START", "PRO", "ULTRA"]
    out: List[Tuple[str, Dict[str, Any]]] = []
    for k in order:
        if k in plans and isinstance(plans[k], dict):
            out.append((k, plans[k]))
    # Add others (e.g., START_FIRST) at the end
    for k, v in plans.items():
        if k not in dict(out) and isinstance(v, dict):
            out.append((k, v))
    return out


def _sorted_topups_for_buttons(kind: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
    """
    kind:
      - None: all
      - "text": only add_text
      - "photo": only add_photo/add_img
    """
    topups = _topups()
    items: List[Tuple[str, Dict[str, Any]]] = []
    for k, v in topups.items():
        if not isinstance(v, dict):
            continue
        add_text = int(_safe_get(v, "add_text", 0) or 0)
        add_photo = int(_safe_get(v, "add_photo", 0) or 0)
        add_img = int(_safe_get(v, "add_img", 0) or 0)  # backward compat
        is_text = add_text > 0
        is_photo = (add_photo > 0) or (add_img > 0)

        if kind == "text" and not is_text:
            continue
        if kind == "photo" and not is_photo:
            continue

        items.append((k, v))

    # Sort: cheaper first
    def _price(item: Tuple[str, Dict[str, Any]]) -> int:
        try:
            return int(_safe_get(item[1], "price_stars", 10**9))
        except Exception:
            return 10**9

    items.sort(key=_price)
    return items


# ---- Messages (public) ----
def paywall_message_early() -> str:
    return (
        "Похоже, ты упёрся(лась) в лимит на сегодня.\n\n"
        "⭐ Подписка увеличит лимиты (текст + фото-разборы) и уберёт ограничения."
    )


def paywall_message_soft() -> str:
    return (
        "Лимит на сегодня закончился.\n\n"
        "Можно продолжить прямо сейчас:\n"
        "• оформить ⭐ подписку\n"
        "• или 🛒 докупить пакеты"
    )


def paywall_message_limit() -> str:
    return (
        "🚫 Лимит исчерпан.\n\n"
        "Чтобы продолжить, оформи ⭐ подписку или 🛒 докупи пакет."
    )


# ---- Keyboards (public) ----
def paywall_keyboard() -> InlineKeyboardMarkup:
    """
    Compact keyboard: Subscribe + Topups + Profile.
    Callback data is intentionally generic; your handlers should route it.
    """
    rows: List[List[InlineKeyboardButton]] = []

    # Subscribe button
    rows.append([_mk_btn("⭐ Подписка", "menu:sub")])

    # Topups shortcut
    rows.append([_mk_btn("🛒 Докупить", "menu:topup")])

    # Back/Profile
    rows.append([_mk_btn("👤 Профиль", "menu:profile"), _mk_btn("⬅️ Назад", "menu:home")])

    return _mk_kb(rows)


def paywall_keyboard_full() -> InlineKeyboardMarkup:
    """
    Full keyboard: show plans and most popular topups if available.
    Uses callback formats:
      - "buy:plan:<PLAN_KEY>"
      - "buy:topup:<TOPUP_KEY>"
    """
    rows: List[List[InlineKeyboardButton]] = []

    plan_items = _sorted_plans_for_buttons()
    if plan_items:
        # One plan per row (clean & readable)
        for plan_key, p in plan_items[:5]:
            price = _fmt_stars(_safe_get(p, "price_stars", ""))
            title = _safe_get(p, "title", plan_key)
            rows.append([_mk_btn(f"⭐ {title} — {price}", f"buy:plan:{plan_key}")])
    else:
        rows.append([_mk_btn("⭐ Подписка", "menu:sub")])

    # Popular topups: show up to 3 text + 3 photo
    text_topups = _sorted_topups_for_buttons("text")[:3]
    photo_topups = _sorted_topups_for_buttons("photo")[:3]

    if text_topups:
        for k, t in text_topups:
            title = _safe_get(t, "title", k)
            price = _fmt_stars(_safe_get(t, "price_stars", ""))
            rows.append([_mk_btn(f"💬 {title} — {price}", f"buy:topup:{k}")])

    if photo_topups:
        for k, t in photo_topups:
            title = _safe_get(t, "title", k)
            price = _fmt_stars(_safe_get(t, "price_stars", ""))
            # Use 📸 label
            rows.append([_mk_btn(f"📸 {title} — {price}", f"buy:topup:{k}")])

    rows.append([_mk_btn("🛒 Все докупы", "menu:topup")])
    rows.append([_mk_btn("⬅️ Назад", "menu:home")])

    return _mk_kb(rows)


# ---- Photo-specific paywall (optional, but very useful) ----
def photo_paywall_message() -> str:
    return (
        "📸 Лимит фото-разборов на сегодня закончился.\n\n"
        "Хочешь продолжить — оформи ⭐ подписку или докупи пакет фото-разборов."
    )


def photo_paywall_keyboard() -> InlineKeyboardMarkup:
    """
    Shows only photo topups + subscription.
    """
    rows: List[List[InlineKeyboardButton]] = []

    photo_topups = _sorted_topups_for_buttons("photo")
    # Show up to 3 best
    for k, t in photo_topups[:3]:
        title = _safe_get(t, "title", k)
        price = _fmt_stars(_safe_get(t, "price_stars", ""))
        rows.append([_mk_btn(f"📸 {title} — {price}", f"buy:topup:{k}")])

    rows.append([_mk_btn("⭐ Подписка", "menu:sub")])
    rows.append([_mk_btn("🛒 Все докупы", "menu:topup"), _mk_btn("⬅️ Назад", "menu:home")])
    return _mk_kb(rows)


# ---- DB compatibility function expected by bot.py ----
async def paywall_trigger_count_for_user(conn, user_id: int) -> int:
    """
    Returns how many times paywall was triggered for the user.
    This is used to choose messaging intensity (early/soft/hard).
    Safe fallback implementation.

    Expected DB schema:
      users(user_id BIGINT PRIMARY KEY, paywall_count INT DEFAULT 0, ...)

    If table/column doesn't exist, returns 0 (no crash).
    """
    try:
        row = await conn.fetchrow(
            "SELECT paywall_count FROM users WHERE user_id=$1",
            user_id,
        )
        if row and row.get("paywall_count") is not None:
            return int(row["paywall_count"])
    except Exception:
        return 0
    return 0


async def bump_paywall_trigger_count(conn, user_id: int) -> None:
    """
    Optional helper: increments users.paywall_count safely.
    If schema doesn't contain column, it's a no-op.
    """
    try:
        await conn.execute(
            "UPDATE users SET paywall_count = COALESCE(paywall_count, 0) + 1 WHERE user_id=$1",
            user_id,
        )
    except Exception:
        return
