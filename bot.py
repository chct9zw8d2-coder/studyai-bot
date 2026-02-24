import os
import time
import json
import random
import hashlib
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

import db
from config import (
    TELEGRAM_BOT_TOKEN,
    OWNER_USER_ID,
    ADMIN_CHAT_ID,
    PLANS,
    TOPUPS,
    STARS_CURRENCY,
    SUBSCRIBE_DAYS_DEFAULT,
    STABILITY_API_KEY,
    STABILITY_ENDPOINT,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_VISION_MODEL,
    DEEPSEEK_BASE_URL,
    MAX_TOKENS,
    ENABLE_TEXT_CACHE,
    ENABLE_IMAGE_CACHE,
    TEXT_CACHE_TTL_DAYS,
    IMAGE_CACHE_TTL_DAYS,
)

from i18n import tr

from ai.deepseek import deepseek_chat, deepseek_vision
from ai.stability_image import generate_image_bytes

from monetization.smart_paywall import (
    PAYWALL_TRIGGER_COUNT,
    paywall_keyboard,
    paywall_keyboard_full,
    paywall_message_early,
    paywall_message_soft,
    paywall_message_limit,
    paywall_trigger_count_for_user,
)
from monetization.trial_system import (
    has_trial,
    start_trial,
    is_trial_active,
)
from monetization.dynamic_limits import (
    limits_for_plan,
)
from monetization.first_purchase_bonus import (
    first_purchase_bonus_available,
    apply_first_purchase_bonus,
)
from monetization.weekly_deals import (
    get_week_deal_for_user,
)
from monetization.personal_offers import (
    recommend_plan_for_user,
    get_personal_offer_for_user,
)
from monetization.behavior_offers import (
    should_offer_after_action,
)
from monetization.photo_paywall import (
    should_paywall_on_photo,
)
from monetization.profit_guard import (
    clamp_text,
    clamp_image,
)
from security.anti_abuse import (
    anti_abuse_check,
)

# ----------------------------
# Helpers
# ----------------------------

def is_owner(user_id: int) -> bool:
    try:
        return str(user_id) == str(OWNER_USER_ID)
    except Exception:
        return False

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    # если в БД есть язык — бери из БД, иначе ru
    try:
        uid = update.effective_user.id if update and update.effective_user else None
        if uid:
            return db.get_lang(uid) or "ru"
    except Exception:
        pass
    return "ru"

def make_cache_key(prefix: str, text: str) -> str:
    h = hashlib.sha256((prefix + ":" + text).encode("utf-8")).hexdigest()
    return h

def now_ts() -> int:
    return int(time.time())

def sub_menu(lang: str, uid: int):
    # меню подписки / оплаты
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ START", callback_data="menu:sub:start")],
        [InlineKeyboardButton("🚀 PRO", callback_data="menu:sub:pro")],
        [InlineKeyboardButton("🔥 ULTRA", callback_data="menu:sub:ultra")],
        [InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")],
    ])

def main_menu(lang: str, uid: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Учёба", callback_data="menu:study")],
        [InlineKeyboardButton("🧠 ОГЭ / ЕГЭ", callback_data="menu:ege")],
        [InlineKeyboardButton("🖼 Создать изображение", callback_data="menu:image")],
        [InlineKeyboardButton("📷 Проверить фото ДЗ", callback_data="menu:photo")],
        [InlineKeyboardButton("🎮 Отвлечься", callback_data="menu:fun")],
        [InlineKeyboardButton("👤 Профиль", callback_data="menu:profile")],
        [InlineKeyboardButton("⭐ Подписка", callback_data="menu:sub")],
    ])

# ----------------------------
# Startup / health
# ----------------------------

def startup_healthcheck():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if not DEEPSEEK_BASE_URL:
        missing.append("DEEPSEEK_BASE_URL")
    if not DEEPSEEK_MODEL:
        missing.append("DEEPSEEK_MODEL")
    if not DEEPSEEK_VISION_MODEL:
        missing.append("DEEPSEEK_VISION_MODEL")
    if not STABILITY_API_KEY:
        missing.append("STABILITY_API_KEY")
    if not STABILITY_ENDPOINT:
        missing.append("STABILITY_ENDPOINT")
    if missing:
        print("❌ Missing required env vars:", ", ".join(missing))
    else:
        print("✅ Required env vars: OK")

# ----------------------------
# Core flows
# ----------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    uid = update.effective_user.id

    try:
        db.ensure_user(uid, update.effective_user.username or "")
        db.inc_activity(uid, "start")
    except Exception:
        pass

    text = (
        "📚 *StudyAI — Учебный помощник*\n\n"
        "Выбирай раздел ниже 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu(lang, uid))

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(update, context)
    if not is_owner(uid):
        await update.message.reply_text("⛔ Нет доступа.")
        return

    stats = db.admin_stats()
    msg = (
        "👑 *Админ панель*\n\n"
        f"Пользователи: {stats.get('users', 0)}\n"
        f"Активные сегодня: {stats.get('active_today', 0)}\n"
        f"Покупок: {stats.get('purchases', 0)}\n"
        f"Выручка (stars): {stats.get('revenue_stars', 0)}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = get_lang(update, context)
    uid = q.from_user.id
    data = q.data or ""

    try:
        db.ensure_user(uid, q.from_user.username or "")
        db.inc_activity(uid, "menu")
    except Exception:
        pass

    if data == "menu:home":
        await q.edit_message_text("📚 *StudyAI — Учебный помощник*", parse_mode="Markdown", reply_markup=main_menu(lang, uid))
        return

    if data == "menu:study":
        await q.edit_message_text(
            "📖 *Учёба*\n\n"
            "Просто напиши вопрос текстом (и я отвечу через DeepSeek).",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")]]),
        )
        context.user_data["mode"] = "text"
        return

    if data == "menu:ege":
        await q.edit_message_text(
            "🧠 *ОГЭ / ЕГЭ*\n\nВыбери предмет:",
            parse_mode="Markdown",
            reply_markup=ege_subjects_keyboard(),
        )
        context.user_data["mode"] = "ege"
        return

    if data == "menu:image":
        await q.edit_message_text(
            "🖼 *Создать изображение*\n\n"
            "Напиши, что нужно нарисовать (подробно, одним сообщением).",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")]]),
        )
        context.user_data["mode"] = "image"
        return

    if data == "menu:photo":
        await q.edit_message_text(
            "📷 *Проверить фото ДЗ*\n\n"
            "Отправь фото с домашкой — я проверю и объясню решение.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")]]),
        )
        context.user_data["mode"] = "photo"
        return

    if data == "menu:fun":
        await q.edit_message_text(
            "🎮 *Отвлечься*\n\n"
            "Выбирай:",
            parse_mode="Markdown",
            reply_markup=fun_keyboard(lang),
        )
        context.user_data["mode"] = "fun"
        return

    if data == "menu:profile":
        plan, expires, text_left, img_left = db.profile(uid)
        msg = (
            "👤 *Профиль*\n\n"
            f"ID: `{uid}`\n"
            f"План: *{plan}*\n"
            f"Подписка до: *{expires or '-'}*\n"
            f"Осталось текстовых ответов сегодня: *{text_left}*\n"
            f"Осталось изображений сегодня: *{img_left}*\n"
        )
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")]]))
        return

    if data == "menu:sub":
        await q.edit_message_text(
            "⭐ *Подписка*\n\nВыбери тариф:",
            parse_mode="Markdown",
            reply_markup=sub_menu(lang, uid),
        )
        return

    # обработка выбора подписки
    if data.startswith("menu:sub:"):
        _, _, plan_key = data.split(":", 2)
        await show_paywall_invoice(q, context, plan_key)
        return

    # игры
    if data.startswith("fun:"):
        await handle_fun_callback(q, context, data)
        return

    # ЕГЭ предмет
    if data.startswith("ege:"):
        await handle_ege_callback(q, context, data)
        return

async def show_paywall_invoice(q, context: ContextTypes.DEFAULT_TYPE, plan_key: str):
    lang = get_lang(None, context)
    uid = q.from_user.id

    # демо: здесь у тебя может быть своя логика выставления invoice в Stars
    # оставляем, как было в проекте — если invoice уже реализован
    try:
        ok = await db.send_stars_invoice(q, plan_key, currency=STARS_CURRENCY)
        if not ok:
            await q.edit_message_text("⚠️ Оплата сейчас недоступна. Попробуй позже.", reply_markup=sub_menu(lang, uid))
    except Exception as e:
        print("INVOICE_ERROR:", repr(e))
        await q.edit_message_text("⚠️ Ошибка оплаты. Попробуй позже.", reply_markup=sub_menu(lang, uid))

# ----------------------------
# EGE keyboard + fun
# ----------------------------

def ege_subjects_keyboard():
    # больше предметов
    subjects = [
        ("Математика", "math"),
        ("Русский язык", "rus"),
        ("Информатика", "info"),
        ("Физика", "phys"),
        ("Химия", "chem"),
        ("Биология", "bio"),
        ("Обществознание", "soc"),
        ("История", "hist"),
        ("Английский", "eng"),
        ("География", "geo"),
        ("Литература", "lit"),
    ]
    rows = []
    for name, key in subjects:
        rows.append([InlineKeyboardButton(name, callback_data=f"ege:{key}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)

def fun_keyboard(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 Логическая задача", callback_data="fun:logic")],
        [InlineKeyboardButton("❓ Правда или миф", callback_data="fun:myth")],
        [InlineKeyboardButton("🧠 IQ-вопрос", callback_data="fun:iq")],
        [InlineKeyboardButton("🕵️ Угадай факт", callback_data="fun:fact")],
        [InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")],
    ])

async def handle_fun_callback(q, context: ContextTypes.DEFAULT_TYPE, data: str):
    lang = get_lang(None, context)
    uid = q.from_user.id
    kind = data.split(":", 1)[1]

    if kind == "logic":
        task = random.choice([
            "Если 3 кошки ловят 3 мыши за 3 минуты, сколько кошек нужно, чтобы поймать 100 мышей за 100 минут?",
            "У тебя есть 2 верёвки, каждая горит ровно 60 минут, но неравномерно. Как отмерить 45 минут?",
            "Что тяжелее: килограмм ваты или килограмм железа?",
        ])
        await q.edit_message_text(f"🧩 *Задача*\n\n{task}", parse_mode="Markdown", reply_markup=fun_keyboard(lang))
        return

    if kind == "myth":
        item = random.choice([
            ("Молния никогда не бьёт в одно место дважды.", "❌ Миф. Может бить много раз."),
            ("У человека и банана 50% общего ДНК.", "✅ Правда (в популярном смысле сравнения генов)."),
            ("Акулы не болеют раком.", "❌ Миф. Болeют."),
        ])
        await q.edit_message_text(f"❓ *Правда или миф*\n\n*{item[0]}*\n\n{item[1]}", parse_mode="Markdown", reply_markup=fun_keyboard(lang))
        return

    if kind == "iq":
        qst = random.choice([
            ("Сколько будет 9×9?", "81"),
            ("Продолжи ряд: 2, 4, 8, 16, ...", "32"),
            ("Если у тебя 3 яблока и ты отдашь одно, сколько останется?", "2"),
        ])
        await q.edit_message_text(f"🧠 *IQ-вопрос*\n\n{qst[0]}\n\nОтвет: ||{qst[1]}||", parse_mode="Markdown", reply_markup=fun_keyboard(lang))
        return

    if kind == "fact":
        fact = random.choice([
            "У осьминога 3 сердца.",
            "Пчёлы могут узнавать лица.",
            "Венера вращается в обратную сторону по сравнению с Землёй.",
        ])
        await q.edit_message_text(f"🕵️ *Факт*\n\n{fact}", parse_mode="Markdown", reply_markup=fun_keyboard(lang))
        return

# ----------------------------
# EGE flow callback
# ----------------------------

async def handle_ege_callback(q, context: ContextTypes.DEFAULT_TYPE, data: str):
    lang = get_lang(None, context)
    uid = q.from_user.id
    subj = data.split(":", 1)[1]
    context.user_data["ege_subject"] = subj

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📘 Теория", callback_data="ege_action:theory")],
        [InlineKeyboardButton("📝 Практика", callback_data="ege_action:practice")],
        [InlineKeyboardButton("✅ Тест", callback_data="ege_action:test")],
        [InlineKeyboardButton("🔎 Разбор", callback_data="ege_action:analysis")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu:ege")],
    ])
    await q.edit_message_text("Выбери режим:", reply_markup=kb)

async def ege_action_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = get_lang(update, context)
    uid = q.from_user.id

    if not q.data.startswith("ege_action:"):
        return

    action = q.data.split(":", 1)[1]
    subj = context.user_data.get("ege_subject", "math")
    context.user_data["mode"] = "ege_text"
    context.user_data["ege_action"] = action

    await q.edit_message_text(
        f"🧠 ОГЭ/ЕГЭ — *{subj}* / *{action}*\n\n"
        "Напиши вопрос/тему, и я отвечу.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="menu:ege")]]),
    )

# ----------------------------
# Message handling (text + image prompts)
# ----------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    uid = update.effective_user.id
    text = (update.message.text or "").strip()

    # анти-абьюз
    if not anti_abuse_check(uid, text):
        await update.message.reply_text("⛔ Слишком много запросов. Попробуй позже.")
        return

    # owner без лимитов
    if not is_owner(uid):
        plan, p, text_left, img_left, *_ = db.remaining_today(uid)
        if text_left <= 0:
            await update.message.reply_text(
                tr(lang, "limit_reached_text") + "\n\n" + tr(lang, "upsell"),
                reply_markup=sub_menu(lang, uid)
            )
            return
        db.inc_usage(uid, "text", 1)

    mode = context.user_data.get("mode", "text")

    # EGE текстовые ответы — просто как текстовый вопрос
    if mode in ("text", "ege_text"):
        await update.message.chat.send_action(action=ChatAction.TYPING)
        reply = await answer_text(uid, lang, text)
        await update.message.reply_text(reply)
        return

    if mode == "image":
        await update.message.chat.send_action(action=ChatAction.UPLOAD_PHOTO)
        await handle_image(update, context, text)
        return

    # default fallback
    await update.message.reply_text("Выбери раздел в меню: /start")

async def answer_text(uid: int, lang: str, prompt: str) -> str:
    prompt = clamp_text(prompt)

    cache_key = make_cache_key("text", prompt)
    if ENABLE_TEXT_CACHE:
        cached = db.cache_get(cache_key)
        if cached:
            return cached

    try:
        resp = await deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_MODEL,
            prompt=prompt,
            max_tokens=MAX_TOKENS,
        )
    except Exception as e:
        print("DEEPSEEK_TEXT_ERROR:", repr(e))
        resp = "⚠️ Ошибка ответа. Попробуй позже."

    if ENABLE_TEXT_CACHE and resp and not resp.startswith("⚠️"):
        db.cache_set(cache_key, resp, ttl_days=TEXT_CACHE_TTL_DAYS)

    return resp

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    uid = update.effective_user.id

    photos = update.message.photo or []
    if not photos:
        await update.message.reply_text("Пришли фото.")
        return

    # paywall на фото для не владельца
    if not is_owner(uid):
        if should_paywall_on_photo(uid):
            await update.message.reply_text(paywall_message_soft(), reply_markup=paywall_keyboard_full())
            return

        plan, p, text_left, img_left, *_ = db.remaining_today(uid)
        if text_left <= 0:
            await update.message.reply_text(
                tr(lang, "limit_reached_text") + "\n\n" + tr(lang, "upsell"),
                reply_markup=sub_menu(lang, uid)
            )
            return
        db.inc_usage(uid, "text", 1)

    # скачать фото
    file = await photos[-1].get_file()
    img_bytes = await file.download_as_bytearray()

    await update.message.chat.send_action(action=ChatAction.TYPING)

    try:
        resp = await deepseek_vision(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            model=DEEPSEEK_VISION_MODEL,
            image_bytes=bytes(img_bytes),
            prompt="Проверь домашнее задание на фото. Найди ошибки и объясни решение по шагам.",
            max_tokens=MAX_TOKENS,
        )
    except Exception as e:
        print("DEEPSEEK_VISION_ERROR:", repr(e))
        resp = "⚠️ Ошибка распознавания. Попробуй позже."

    await update.message.reply_text(resp)

# ----------------------------
# FIXED: handle_image (Stability)
# ----------------------------

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    lang = get_lang(update, context)
    uid = update.effective_user.id

    # Нужен plan_key для промо/офферов и совместимости с maybe_personal_offer
    plan_key, _ = db.get_limits(uid)

    try:
        db.inc_activity(uid, "image")
    except Exception:
        pass

    # Лимиты для обычных пользователей (владелец безлимит)
    if not is_owner(uid):
        plan, p, _, img_left, *_ = db.remaining_today(uid)
        if img_left <= 0:
            await update.message.reply_text(
                tr(lang, "limit_reached_img") + "\n\n" + tr(lang, "upsell"),
                reply_markup=sub_menu(lang, uid),
            )
            return
        db.inc_usage(uid, "img", 1)

    if not STABILITY_API_KEY or not STABILITY_ENDPOINT:
        await update.message.reply_text(tr(lang, "media_not_configured"))
        return

    prompt = clamp_image(prompt)

    # кеш картинок
    cache_key = make_cache_key("img", prompt)
    if ENABLE_IMAGE_CACHE:
        cached_bytes = db.cache_get_bytes(cache_key)
        if cached_bytes:
            await update.message.reply_photo(photo=cached_bytes, caption="🖼 (cache)")
            return

    try:
        img = generate_image_bytes(prompt)
        if ENABLE_IMAGE_CACHE and img:
            db.cache_set_bytes(cache_key, img, ttl_days=IMAGE_CACHE_TTL_DAYS)
        await update.message.reply_photo(photo=img, caption="🖼")
        await maybe_personal_offer(update, context, plan_key)
    except Exception as e:
        # чтобы видеть причину в Railway Logs
        print("IMAGE_GEN_ERROR:", repr(e))
        await update.message.reply_text("⚠️ Ошибка генерации изображения. Попробуй позже.")

# ----------------------------
# Offers / paywall
# ----------------------------

async def maybe_personal_offer(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_key: str):
    uid = update.effective_user.id
    lang = get_lang(update, context)

    if is_owner(uid):
        return

    try:
        if should_offer_after_action(uid, "image"):
            offer = get_personal_offer_for_user(uid, current_plan=plan_key)
            if offer:
                await update.message.reply_text(offer, reply_markup=paywall_keyboard())
    except Exception as e:
        print("OFFER_ERROR:", repr(e))

# ----------------------------
# Payments callbacks placeholder
# ----------------------------

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(update, context)

    try:
        db.on_success_payment(uid, update.message.successful_payment)
    except Exception as e:
        print("PAYMENT_SAVE_ERROR:", repr(e))

    await update.message.reply_text("✅ Подписка активирована! Спасибо ❤️", reply_markup=main_menu(lang, uid))

# ----------------------------
# Main
# ----------------------------

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    startup_healthcheck()
    db.init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))

    app.add_handler(CallbackQueryHandler(menu_router, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(ege_action_router, pattern=r"^ege_action:"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # платежи (если используется Stars / invoices)
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    # precheckout handler добавляй, если реально используешь invoices
    # app.add_handler(PreCheckoutQueryHandler(precheckout_handler))

    print("✅ Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
