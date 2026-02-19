\
"""
StudyAI Bot (Text + Images) + Telegram Stars

- python-telegram-bot v21+
- Pollinations endpoints for text/image (no API keys)
- PostgreSQL via DATABASE_URL
- Plans:
    FREE: small daily limits
    PRO: 499⭐ / 30 days
    VIP: 999⭐ / 30 days
- Add-on packs: extra text / images (daily add-ons)
"""

from __future__ import annotations

import base64
import io
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    InputFile,
)
from telegram.constants import ParseMode
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from db import DB, UserState
from ai.pollinations import generate_text, generate_image_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("studyai-bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN (or BOT_TOKEN) env var")

# Stars payments use currency XTR (Telegram Stars)
CURRENCY = "XTR"

# ---------- Plans / limits ----------

@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    price_stars: int
    days: int
    text_per_day: int
    img_per_day: int


FREE = Plan("free", "Free", 0, 0, text_per_day=10, img_per_day=2)
PRO = Plan("pro", "PRO", 499, 30, text_per_day=120, img_per_day=25)
VIP = Plan("vip", "VIP", 999, 30, text_per_day=300, img_per_day=80)

PLANS = {p.code: p for p in (FREE, PRO, VIP)}

# Add-ons (applied to current day only)
ADDON_TEXT50 = ("addon_text50", "➕ 50 текстовых запросов (на сегодня)", 199, 50, 0)
ADDON_IMG10 = ("addon_img10", "➕ 10 картинок (на сегодня)", 199, 0, 10)

ADDONS = {ADDON_TEXT50[0]: ADDON_TEXT50, ADDON_IMG10[0]: ADDON_IMG10}

# ---------- UI ----------

def main_menu() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton("📝 Текст", callback_data="m:text"),
            InlineKeyboardButton("🖼 Картинка", callback_data="m:image"),
        ],
        [
            InlineKeyboardButton("🎨 Изменить фото", callback_data="m:edit"),
        ],
        [
            InlineKeyboardButton("⭐ Подписка", callback_data="m:plans"),
            InlineKeyboardButton("🛒 Докупить", callback_data="m:addons"),
        ],
        [
            InlineKeyboardButton("👤 Профиль/Лимиты", callback_data="m:profile"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="m:help"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def plans_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("⭐ PRO — 499 Stars / 30 дней", callback_data="buy:plan:pro")],
        [InlineKeyboardButton("👑 VIP — 999 Stars / 30 дней", callback_data="buy:plan:vip")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="m:home")],
    ]
    return InlineKeyboardMarkup(kb)


def addons_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("➕ 50 текстов — 199⭐ (на сегодня)", callback_data="buy:addon:addon_text50")],
        [InlineKeyboardButton("➕ 10 картинок — 199⭐ (на сегодня)", callback_data="buy:addon:addon_img10")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="m:home")],
    ]
    return InlineKeyboardMarkup(kb)


HELP_TEXT = (
    "🤖 *StudyAI* — быстрые ответы и реалистичные картинки.\n\n"
    "*Как пользоваться:*\n"
    "• Нажми *📝 Текст* и напиши запрос.\n"
    "• Нажми *🖼 Картинка* и напиши описание (чем подробнее — тем лучше).\n"
    "• Нажми *🎨 Изменить фото* → пришли фото + подпись/описание, что изменить.\n\n"
    "*Лимиты обновляются каждые сутки (UTC).*"
)

WELCOME = (
    "Привет! Я *StudyAI* 🤖\n\n"
    "Я быстро отвечаю на вопросы и создаю реалистичные картинки по тексту, "
    "а ещё могу *изменять* загруженные изображения.\n\n"
    "Выбери действие в меню ниже 👇"
)

# ---------- Helpers ----------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def today_utc() -> date:
    return now_utc().date()

def fmt_dt(d: Optional[datetime]) -> str:
    if not d:
        return "—"
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def user_effective_plan(u: UserState) -> Plan:
    # If subscription active -> that plan else FREE
    if u.plan in PLANS and u.sub_expires_at and u.sub_expires_at > now_utc():
        if u.plan in ("pro", "vip"):
            return PLANS[u.plan]
    return FREE

def ensure_daily_reset(db: DB, u: UserState) -> UserState:
    if u.last_reset_date != today_utc():
        u = db.reset_daily(u.user_id, today_utc())
    return u

def can_use_text(u: UserState) -> bool:
    plan = user_effective_plan(u)
    limit = plan.text_per_day + u.addon_text_left
    return u.text_used_today < limit

def can_use_image(u: UserState) -> bool:
    plan = user_effective_plan(u)
    limit = plan.img_per_day + u.addon_img_left
    return u.img_used_today < limit

def remaining_text(u: UserState) -> int:
    plan = user_effective_plan(u)
    return max(0, (plan.text_per_day + u.addon_text_left) - u.text_used_today)

def remaining_img(u: UserState) -> int:
    plan = user_effective_plan(u)
    return max(0, (plan.img_per_day + u.addon_img_left) - u.img_used_today)

def profile_text(u: UserState) -> str:
    plan = user_effective_plan(u)
    active = "✅ активна" if plan.code != "free" else "—"
    exp = fmt_dt(u.sub_expires_at) if plan.code != "free" else "—"
    return (
        f"👤 *Профиль*\n\n"
        f"*Тариф:* {plan.title}\n"
        f"*Подписка:* {active}\n"
        f"*Истекает:* {exp}\n\n"
        f"*Лимиты на сегодня (UTC):*\n"
        f"• Текст: {u.text_used_today} / {plan.text_per_day + u.addon_text_left} "
        f"(осталось {remaining_text(u)})\n"
        f"• Картинки: {u.img_used_today} / {plan.img_per_day + u.addon_img_left} "
        f"(осталось {remaining_img(u)})\n\n"
        f"⚡️ Хочешь больше — оформи подписку или докупи пакеты."
    )

# ---------- Commands / Callbacks ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = DB()
    user_id = update.effective_user.id
    db.ensure_user(user_id)
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = DB()
    u = ensure_daily_reset(db, db.ensure_user(update.effective_user.id))
    await update.message.reply_text(profile_text(u), parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())

async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline menu router."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    db = DB()
    u = ensure_daily_reset(db, db.ensure_user(query.from_user.id))

    if data == "m:home":
        await query.edit_message_text(WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())
        db.set_mode(u.user_id, "idle")
        return

    if data == "m:help":
        await query.edit_message_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())
        db.set_mode(u.user_id, "idle")
        return

    if data == "m:profile":
        await query.edit_message_text(profile_text(u), parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu())
        db.set_mode(u.user_id, "idle")
        return

    if data == "m:plans":
        text = (
            "⭐ *Подписка на 30 дней*\n\n"
            "• *PRO 499⭐*: много текстов + картинок, быстрый доступ.\n"
            "• *VIP 999⭐*: максимум лимитов для активной работы.\n\n"
            "_Автопродление:_ Telegram Stars не списывает автоматически без подтверждения. "
            "Мы заранее пришлём счёт на продление — оплатишь в 1 тап.\n"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=plans_menu())
        db.set_mode(u.user_id, "idle")
        return

    if data == "m:addons":
        await query.edit_message_text(
            "🛒 *Докупить лимиты на сегодня*\n\nВыбери пакет:", parse_mode=ParseMode.MARKDOWN, reply_markup=addons_menu()
        )
        db.set_mode(u.user_id, "idle")
        return

    if data == "m:text":
        db.set_mode(u.user_id, "await_text")
        await query.edit_message_text(
            "📝 Напиши запрос *одним сообщением*.\n\nПример: `Объясни, что такое гипотенуза простыми словами`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    if data == "m:image":
        db.set_mode(u.user_id, "await_image_prompt")
        await query.edit_message_text(
            "🖼 Напиши описание картинки.\n\nПример: `Реалистичный кот в костюме астронавта, студийный свет, 4k`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    if data == "m:edit":
        db.set_mode(u.user_id, "await_edit_image")
        await query.edit_message_text(
            "🎨 Пришли *фото* и добавь *подпись*, что изменить.\n\n"
            "Пример подписи: `Сделай фон ночным городом и добавь неоновую подсветку`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    # Buy routes
    if data.startswith("buy:plan:"):
        plan_code = data.split(":")[-1]
        if plan_code not in PLANS or plan_code == "free":
            await query.edit_message_text("Неизвестный тариф.", reply_markup=main_menu())
            return
        await send_invoice_for_plan(query, plan_code)
        return

    if data.startswith("buy:addon:"):
        addon_code = data.split(":")[-1]
        if addon_code not in ADDONS:
            await query.edit_message_text("Неизвестный пакет.", reply_markup=main_menu())
            return
        await send_invoice_for_addon(query, addon_code)
        return


async def send_invoice_for_plan(query, plan_code: str) -> None:
    plan = PLANS[plan_code]
    title = f"StudyAI — {plan.title} на {plan.days} дней"
    description = "Подписка открывает повышенные лимиты на текст и картинки."
    payload = f"plan:{plan_code}"
    prices = [LabeledPrice(label=title, amount=plan.price_stars)]
    await query.message.reply_invoice(
        title=title,
        description=description,
        payload=payload,
        currency=CURRENCY,
        prices=prices,
    )

async def send_invoice_for_addon(query, addon_code: str) -> None:
    code, title, price, t_add, i_add = ADDONS[addon_code]
    description = "Пакет добавляется к лимитам *на сегодня (UTC)*."
    payload = f"addon:{addon_code}"
    prices = [LabeledPrice(label=title, amount=price)]
    await query.message.reply_invoice(
        title=title,
        description=description,
        payload=payload,
        currency=CURRENCY,
        prices=prices,
    )

async def on_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer pre-checkout queries."""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sp = update.message.successful_payment
    payload = sp.invoice_payload
    user_id = update.effective_user.id
    db = DB()
    u = ensure_daily_reset(db, db.ensure_user(user_id))

    if payload.startswith("plan:"):
        plan_code = payload.split(":", 1)[1]
        plan = PLANS.get(plan_code)
        if not plan:
            await update.message.reply_text("Платёж получен, но тариф не распознан.", reply_markup=main_menu())
            return
        # Extend from max(now, existing expiry)
        start = max(now_utc(), u.sub_expires_at or now_utc())
        expires = start + timedelta(days=plan.days)
        db.set_subscription(user_id, plan_code, expires)
        await update.message.reply_text(
            f"✅ Подписка *{plan.title}* активна!\nИстекает: *{fmt_dt(expires)}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    if payload.startswith("addon:"):
        addon_code = payload.split(":", 1)[1]
        addon = ADDONS.get(addon_code)
        if not addon:
            await update.message.reply_text("Платёж получен, но пакет не распознан.", reply_markup=main_menu())
            return
        _, title, _, t_add, i_add = addon
        db.add_addons_today(user_id, t_add, i_add)
        u = db.get_user(user_id)
        await update.message.reply_text(
            f"✅ Готово! *{title}*\n\nТеперь осталось:\n"
            f"• Текст: {remaining_text(u)}\n"
            f"• Картинки: {remaining_img(u)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    await update.message.reply_text("✅ Платёж получен!", reply_markup=main_menu())

# ---------- Message processing ----------

async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user text depending on current mode."""
    if not update.message:
        return
    user_id = update.effective_user.id
    db = DB()
    u = ensure_daily_reset(db, db.ensure_user(user_id))

    # Allow /text style
    if update.message.text and update.message.text.startswith("/text"):
        parts = update.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await update.message.reply_text("Напишите: /text ваш запрос\nПример: /text Объясни гипотенузу", reply_markup=main_menu())
            return
        prompt = parts[1].strip()
        await handle_text_prompt(update, prompt, db, u)
        return

    mode = u.mode or "idle"

    # If user wrote plain text while idle -> treat as text prompt (quality UX)
    if mode in ("idle", "await_text"):
        prompt = (update.message.text or "").strip()
        if not prompt:
            return
        await handle_text_prompt(update, prompt, db, u)
        return

    if mode == "await_image_prompt":
        prompt = (update.message.text or "").strip()
        if not prompt:
            await update.message.reply_text("Напиши описание картинки текстом 🙂", reply_markup=main_menu())
            return
        await handle_image_prompt(update, prompt, db, u)
        return

    # In edit mode, user must send photo with caption. If they send text, remind.
    if mode == "await_edit_image":
        await update.message.reply_text("Пришли фото и подпись, что изменить 🙂", reply_markup=main_menu())
        return


async def handle_text_prompt(update: Update, prompt: str, db: DB, u: UserState) -> None:
    u = ensure_daily_reset(db, u)
    if not can_use_text(u):
        await update.message.reply_text(
            "⛔️ Лимит текстовых запросов на сегодня исчерпан.\n"
            "Оформи подписку ⭐ или докупи пакет 🛒",
            reply_markup=main_menu(),
        )
        return

    await update.message.chat.send_action("typing")
    try:
        answer = generate_text(prompt)
    except Exception as e:
        log.exception("Text generation error")
        await update.message.reply_text(f"Ошибка генерации текста: {e}", reply_markup=main_menu())
        return

    db.consume_text(u.user_id, 1)
    db.set_mode(u.user_id, "idle")
    await update.message.reply_text(answer, reply_markup=main_menu())


async def handle_image_prompt(update: Update, prompt: str, db: DB, u: UserState) -> None:
    u = ensure_daily_reset(db, u)
    if not can_use_image(u):
        await update.message.reply_text(
            "⛔️ Лимит картинок на сегодня исчерпан.\n"
            "Оформи подписку ⭐ или докупи пакет 🛒",
            reply_markup=main_menu(),
        )
        return

    await update.message.chat.send_action("upload_photo")
    try:
        img_bytes = generate_image_bytes(prompt)
    except Exception as e:
        log.exception("Image generation error")
        await update.message.reply_text(f"Ошибка генерации картинки: {e}", reply_markup=main_menu())
        return

    db.consume_image(u.user_id, 1)
    db.set_mode(u.user_id, "idle")
    bio = io.BytesIO(img_bytes)
    bio.name = "image.png"
    await update.message.reply_photo(photo=InputFile(bio), caption="✅ Готово", reply_markup=main_menu())


async def on_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo uploads for edit mode."""
    if not update.message:
        return
    user_id = update.effective_user.id
    db = DB()
    u = ensure_daily_reset(db, db.ensure_user(user_id))

    if (u.mode or "idle") != "await_edit_image":
        await update.message.reply_text(
            "Фото получено. Если хочешь *изменить* фото — нажми 🎨 *Изменить фото* и пришли фото с подписью.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return

    if not can_use_image(u):
        await update.message.reply_text(
            "⛔️ Лимит картинок на сегодня исчерпан.\n"
            "Оформи подписку ⭐ или докупи пакет 🛒",
            reply_markup=main_menu(),
        )
        return

    caption = (update.message.caption or "").strip()
    if not caption:
        await update.message.reply_text("Добавь подпись: что именно изменить на фото 🙂", reply_markup=main_menu())
        return

    # Get highest resolution photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()

    await update.message.chat.send_action("upload_photo")
    try:
        edited = generate_image_bytes(caption, image_bytes=bytes(photo_bytes))
    except Exception as e:
        log.exception("Image edit error")
        await update.message.reply_text(f"Ошибка изменения картинки: {e}", reply_markup=main_menu())
        return

    db.consume_image(u.user_id, 1)
    db.set_mode(u.user_id, "idle")
    bio = io.BytesIO(edited)
    bio.name = "edited.png"
    await update.message.reply_photo(photo=InputFile(bio), caption="✅ Готово", reply_markup=main_menu())

# ---------- Main ----------

def build_app() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("profile", cmd_profile))

    # Payments
    application.add_handler(PreCheckoutQueryHandler(on_precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))

    # Menu callbacks
    application.add_handler(CallbackQueryHandler(on_menu))

    # Photos (for edit)
    application.add_handler(MessageHandler(filters.PHOTO, on_photo_message))

    # Text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
    application.add_handler(CommandHandler("text", on_text_message))  # /text ...

    return application


def main() -> None:
    # Quick DB check at boot
    DB().migrate()
    log.info("Bot started")
    app = build_app()

    try:
        # Drop pending updates on boot to avoid old queue after downtime
        app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Conflict:
        # This means another instance is already polling the same token.
        # It will keep failing until the other instance stops.
        log.error(
            "Telegram Conflict: another getUpdates request is running. "
            "Stop any other bot instance (local run / second Railway service) using the same token."
        )
        raise


if __name__ == "__main__":
    main()
