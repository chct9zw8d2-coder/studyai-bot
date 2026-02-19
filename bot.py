from __future__ import annotations

import io
import logging
from datetime import timedelta

from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    PreCheckoutQueryHandler, CallbackQueryHandler, filters
)

from config import load_settings, Plan
from db import DB, utcnow, is_active, today_utc
from ai.pollinations import generate_text, generate_image_bytes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("tg-stars-ai-bot")

# --------- UI / Keyboards ---------

def plans_kb(settings) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"⭐ Basic — {settings.plan_basic.price_stars}", callback_data="BUY_BASIC")],
        [InlineKeyboardButton(f"⭐ Pro — {settings.plan_pro.price_stars}", callback_data="BUY_PRO")],
        [InlineKeyboardButton(f"⭐ Ultra — {settings.plan_ultra.price_stars}", callback_data="BUY_ULTRA")],
    ]
    return InlineKeyboardMarkup(rows)

def topup_kb(plan: Plan) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Докупить пакет на сегодня ({plan.topup_price_stars}⭐)", callback_data=f"TOPUP_{plan.name.upper()}")]]
    )

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard for quick actions."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🧠 Задать вопрос"), KeyboardButton("📚 Домашка")],
            [KeyboardButton("📝 Эссе/реферат"), KeyboardButton("💻 Код")],
            [KeyboardButton("🖼️ Картинка"), KeyboardButton("⭐ Тарифы")],
            [KeyboardButton("📊 Статус")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def onboarding_text(settings) -> str:
    return (
        "🎓 *StudyAI — помощник для школы, колледжа и университета*\n\n"
        "Я умею:\n"
        "• решать домашку и объяснять *пошагово*\n"
        "• отвечать на любые вопросы\n"
        "• писать эссе/рефераты\n"
        "• писать и разбирать код\n"
        "• создавать картинки по описанию\n\n"
        "Примеры:\n"
        "• `Реши: 2x+5=15`\n"
        "• `Объясни фотосинтез для 7 класса`\n"
        "• `Напиши эссе на тему...`\n"
        "• `Напиши код на Python...`\n"
        "• `img: кот в очках в стиле аниме`\n\n"
        "Бесплатно (UTC/сутки): "
        f"{settings.free_text_per_day} ответов и {settings.free_img_per_day} картинок.\n"
        "Чтобы начать — нажми кнопку внизу или просто пришли задачу."
    )


def menu_text(settings) -> str:
    return (
        "🎓 *StudyAI (домашка + учеба + картинки)*\n\n"
        "*Бесплатно (UTC/сутки):* "
        f"{settings.free_text_per_day} ответов и {settings.free_img_per_day} картинок\n\n"
        "*Подписки (UTC/сутки):*\n"
        f"• *Basic* — {settings.plan_basic.price_stars}⭐/мес: {settings.plan_basic.text_per_day} ответов, {settings.plan_basic.img_per_day} картинок\n"
        f"• *Pro* — {settings.plan_pro.price_stars}⭐/мес: {settings.plan_pro.text_per_day} ответов, {settings.plan_pro.img_per_day} картинок\n"
        f"• *Ultra* — {settings.plan_ultra.price_stars}⭐/мес: {settings.plan_ultra.text_per_day} ответов, {settings.plan_ultra.img_per_day} картинок\n\n"
        "*Докупка (только при активной подписке):*\n"
        "Если суточный лимит закончился — можно докупить ещё один пакет на текущие сутки.\n\n"
        "Команды:\n"
        "• `/plans` — тарифы\n"
        "• `/buy` — купить подписку\n"
        "• `/topup` — докупить пакет на сегодня (если лимит закончился)\n"
        "• `/status` — статус + лимиты\n"
        "• `/text <запрос>` — текст\n"
        "• `/img <запрос>` — картинка\n\n"
        "Быстро:\n"
        "• Просто напиши сообщение — отвечу текстом\n"
        "• Напиши `img: кот в очках` — пришлю картинку\n"
    )

def _extract_after_command(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""

def _looks_like_image_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("img:") or t.startswith("image:") or t.startswith("картинка:") or t.startswith("фото:")

def _strip_image_prefix(text: str) -> str:
    t = (text or "").strip()
    for pref in ("img:", "image:", "картинка:", "фото:"):
        if t.lower().startswith(pref):
            return t[len(pref):].strip()
    return t

def _build_text_prompt(user_text: str, mode: str | None) -> str:
    """Wrap user prompt with instructions to improve education/coding quality."""
    t = (user_text or "").strip()
    m = (mode or "ask").lower()

    base_rules = (
        "Ты — StudyAI, дружелюбный репетитор для школьников и студентов. "
        "Отвечай по-русски (если пользователь не просит другой язык). "
        "Если данных не хватает — уточни. "
        "Пиши структурно и понятно."
    )

    if m == "homework":
        return (
            base_rules
            + "\n\nЗАДАЧА: " + t
            + "\n\nРешай пошагово, показывай формулы/преобразования. "
              "В конце дай краткий итог/ответ."
        )

    if m == "essay":
        return (
            base_rules
            + "\n\nТЕМА/ЗАДАНИЕ: " + t
            + "\n\nСначала дай краткий план, затем текст. "
              "Пиши 400–900 слов (если не указано иначе)."
        )

    if m == "code":
        return (
            "Ты — опытный разработчик и наставник. "
            "Дай рабочий код. Оформи код в блоках ``` ``` и добавь короткие пояснения. "
            "Если язык не указан — уточни."
            "\n\nЗАПРОС: " + t
        )

    # default
    return (
        base_rules
        + "\n\nВОПРОС: " + t
        + "\n\nЕсли это учебный вопрос — объясняй простыми словами и при необходимости пошагово."
    )

def _enhance_image_prompt(user_text: str) -> str:
    t = (user_text or "").strip()
    return f"{t}, high quality, detailed, sharp"

# --------- Plans / Limits ---------

def _plan_by_name(settings, plan_name: str) -> Plan:
    name = (plan_name or "").strip().lower()
    if name == "basic":
        return settings.plan_basic
    if name == "ultra":
        return settings.plan_ultra
    return settings.plan_pro  # default / fallback

def _get_subscription(db: DB, settings, user_id: int):
    sub = db.get_subscription(user_id)
    if not sub:
        return None, None
    plan = _plan_by_name(settings, sub.get("plan"))
    paid_until = sub.get("paid_until")
    return plan, paid_until

def _sub_status_text(plan: Plan | None, paid_until) -> str:
    if plan and is_active(paid_until):
        return f"✅ Подписка *{plan.name}* активна до: {paid_until.strftime('%Y-%m-%d %H:%M UTC')}"
    if paid_until:
        return f"❌ Подписка закончилась: {paid_until.strftime('%Y-%m-%d %H:%M UTC')}"
    return "ℹ️ Подписка не активна."

def _limits_text_free(settings, usage: dict) -> str:
    t_used = usage.get("text_used", 0)
    i_used = usage.get("img_used", 0)
    return (
        f"Сегодня (UTC) бесплатно: ответы {t_used}/{settings.free_text_per_day}, "
        f"картинки {i_used}/{settings.free_img_per_day}"
    )

def _limits_text_plan(plan: Plan, usage: dict) -> str:
    t_used = usage.get("text_used", 0)
    i_used = usage.get("img_used", 0)
    b_t = usage.get("bonus_text", 0)
    b_i = usage.get("bonus_img", 0)
    t_limit = plan.text_per_day + b_t
    i_limit = plan.img_per_day + b_i
    return (
        f"Сегодня (UTC) {plan.name}: ответы {t_used}/{t_limit}, картинки {i_used}/{i_limit}"
        + (f" (докупка: +{b_t} ответов, +{b_i} картинок)" if (b_t or b_i) else "")
    )

def _can_use_text(settings, plan: Plan | None, paid_until, usage: dict) -> tuple[bool, str]:
    if plan and is_active(paid_until):
        limit = plan.text_per_day + usage.get("bonus_text", 0)
        return usage.get("text_used", 0) < limit, "paid"
    return usage.get("text_used", 0) < settings.free_text_per_day, "free"

def _can_use_img(settings, plan: Plan | None, paid_until, usage: dict) -> tuple[bool, str]:
    if plan and is_active(paid_until):
        limit = plan.img_per_day + usage.get("bonus_img", 0)
        return usage.get("img_used", 0) < limit, "paid"
    return usage.get("img_used", 0) < settings.free_img_per_day, "free"

# --------- Commands ---------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    await update.message.reply_markdown(
        onboarding_text(settings),
        reply_markup=main_menu_kb(),
    )
    await update.message.reply_markdown(
        "⭐ Если хочешь больше лимитов — выбери подписку:",
        reply_markup=plans_kb(settings),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    await update.message.reply_markdown(onboarding_text(settings), reply_markup=main_menu_kb())


async def plans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    await update.message.reply_markdown(menu_text(settings), reply_markup=plans_kb(settings))

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    user_id = update.effective_user.id
    plan, paid_until = _get_subscription(db, settings, user_id)
    usage = db.get_daily_usage(user_id, today_utc())

    if plan and is_active(paid_until):
        limits = _limits_text_plan(plan, usage)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Продлить/сменить тариф", callback_data="OPEN_PLANS")],
        ])
    else:
        limits = _limits_text_free(settings, usage)
        kb = plans_kb(settings)

    await update.message.reply_markdown(
        _sub_status_text(plan, paid_until) + "\n" + limits,
        reply_markup=kb,
    )

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    await update.message.reply_markdown("Выберите тариф:", reply_markup=plans_kb(settings))

async def topup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    user_id = update.effective_user.id
    plan, paid_until = _get_subscription(db, settings, user_id)
    usage = db.get_daily_usage(user_id, today_utc())

    if not (plan and is_active(paid_until)):
        await update.message.reply_text("Докупка доступна только при активной подписке. Открой /buy.")
        return

    # Allow topup any time, but it's most useful when at limit
    await update.message.reply_text(
        "Докупка добавит ещё один пакет на *сегодня (UTC)*:\n"
        f"• +{plan.topup_text} ответов\n"
        f"• +{plan.topup_img} картинок\n\n"
        f"Цена: {plan.topup_price_stars}⭐\n\n"
        "Нажми кнопку ниже. Если Stars не хватает, Telegram предложит докупить Stars.",
        reply_markup=topup_kb(plan),
        parse_mode="Markdown",
    )

# --------- Payments (Stars) ---------

async def send_invoice_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: Plan) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else update.callback_query.message.chat_id

    title = f"Подписка {plan.name} на 30 дней"
    description = (
        f"{plan.text_per_day} ответов/сутки и {plan.img_per_day} картинок/сутки (UTC).\n"
        "Если лимит на сегодня закончился — можно докупить пакет на сегодня.\n"
        "Доступ активируется сразу после оплаты."
    )
    payload = f"SUB_{plan.name.upper()}"
    currency = "XTR"  # Telegram Stars
    prices = [LabeledPrice(f"{plan.name} (30 дней)", plan.price_stars)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # for Stars it is empty
        currency=currency,
        prices=prices,
    )

async def send_invoice_topup(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: Plan) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else update.callback_query.message.chat_id

    title = f"Докупка пакета на сегодня ({plan.name})"
    description = f"Добавляет +{plan.topup_text} ответов и +{plan.topup_img} картинок на текущие сутки (UTC)."
    payload = f"TOPUP_{plan.name.upper()}"
    currency = "XTR"
    prices = [LabeledPrice(f"Пакет на сегодня ({plan.name})", plan.topup_price_stars)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=currency,
        prices=prices,
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]

    sp = update.message.successful_payment
    user_id = update.effective_user.id

    charge_id = sp.telegram_payment_charge_id
    stars_amount = sp.total_amount  # for XTR it's Stars
    payload = sp.invoice_payload or ""

    # Determine kind
    if payload.startswith("SUB_"):
        kind = "subscription"
    elif payload.startswith("TOPUP_"):
        kind = "topup"
    else:
        kind = "unknown"

    inserted = db.record_payment(charge_id, user_id, stars_amount, kind=kind, payload=payload)
    if not inserted:
        await update.message.reply_text("✅ Платёж уже обработан. Проверь /status")
        return

    if payload.startswith("SUB_"):
        plan_name = payload.replace("SUB_", "").strip().lower()
        plan = _plan_by_name(settings, plan_name)

        # Extend if active, otherwise start from now
        current = db.get_subscription(user_id)
        if current and is_active(current.get("paid_until")):
            base = current.get("paid_until")
            new_until = base + timedelta(days=settings.sub_days)
        else:
            new_until = utcnow() + timedelta(days=settings.sub_days)

        db.set_subscription(user_id, plan.name, new_until)

        await update.message.reply_text(
            f"✅ Оплата прошла! Подписка {plan.name} активирована.\n"
            f"Действует до: {new_until.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Лимиты в сутки (UTC): {plan.text_per_day} ответов и {plan.img_per_day} картинок.\n"
            "Если лимит на сегодня закончился — используй /topup."
        )
        return

    if payload.startswith("TOPUP_"):
        plan_name = payload.replace("TOPUP_", "").strip().lower()
        plan = _plan_by_name(settings, plan_name)

        # Allow topup only if subscription active
        sub_plan, paid_until = _get_subscription(db, settings, user_id)
        if not (sub_plan and is_active(paid_until)):
            await update.message.reply_text(
                "⚠️ Докупка доступна только при активной подписке.\n"
                "Похоже, подписка не активна. Напиши /buy чтобы оформить."
            )
            return

        # Add bonus for today (UTC)
        db.add_bonus(user_id, bonus_text=plan.topup_text, bonus_img=plan.topup_img, day_utc=today_utc())
        usage = db.get_daily_usage(user_id, today_utc())

        await update.message.reply_text(
            "✅ Докупка успешна! На сегодня (UTC) добавлен пакет:\n"
            f"• +{plan.topup_text} ответов\n"
            f"• +{plan.topup_img} картинок\n\n"
            + _limits_text_plan(sub_plan, usage)
        )
        return

    await update.message.reply_text("✅ Платёж получен.")

# --------- Callback queries ---------

async def cbq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]

    q = update.callback_query
    await q.answer()

    if q.data == "OPEN_PLANS":
        await q.message.reply_text("Выберите тариф:", reply_markup=plans_kb(settings))
        return

    if q.data in ("BUY_BASIC", "BUY_PRO", "BUY_ULTRA"):
        plan = {
            "BUY_BASIC": settings.plan_basic,
            "BUY_PRO": settings.plan_pro,
            "BUY_ULTRA": settings.plan_ultra,
        }[q.data]
        await send_invoice_subscription(update, context, plan)
        return

    if q.data.startswith("TOPUP_"):
        plan_name = q.data.replace("TOPUP_", "").strip().lower()
        plan = _plan_by_name(settings, plan_name)

        # Check premium active before sending invoice
        user_id = update.effective_user.id
        sub_plan, paid_until = _get_subscription(db, settings, user_id)
        if not (sub_plan and is_active(paid_until)):
            await q.message.reply_text("Докупка доступна только при активной подписке. Открой /buy.")
            return

        await send_invoice_topup(update, context, plan)
        return

# --------- AI handlers ---------

async def text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    user_id = update.effective_user.id

    plan, paid_until = _get_subscription(db, settings, user_id)
    usage = db.get_daily_usage(user_id, today_utc())
    ok, mode = _can_use_text(settings, plan, paid_until, usage)
    if not ok:
        if plan and is_active(paid_until):
            await update.message.reply_text(
                "🔒 Суточный лимит ответов исчерпан (UTC).\n"
                + _limits_text_plan(plan, usage)
                + "\n\nМожно докупить пакет на сегодня:",
                reply_markup=topup_kb(plan),
            )
        else:
            await update.message.reply_text(
                "🔒 Бесплатный лимит ответов на сегодня исчерпан (UTC).\n"
                + _limits_text_free(settings, usage)
                + "\n\nВыбери подписку:",
                reply_markup=plans_kb(settings),
            )
        return

    prompt = _extract_after_command(update.message.text)
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        answer = generate_text(_build_text_prompt(prompt, 'ask'), model=settings.text_model, timeout=settings.request_timeout_sec, max_len=settings.max_prompt_len)
        db.inc_text(user_id, today_utc())
    except Exception as e:
        logger.exception("Text generation failed")
        answer = f"⚠️ Ошибка генерации текста: {e}"
    await update.message.reply_text(answer)

async def img_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    user_id = update.effective_user.id

    plan, paid_until = _get_subscription(db, settings, user_id)
    usage = db.get_daily_usage(user_id, today_utc())
    ok, mode = _can_use_img(settings, plan, paid_until, usage)
    if not ok:
        if plan and is_active(paid_until):
            await update.message.reply_text(
                "🔒 Суточный лимит картинок исчерпан (UTC).\n"
                + _limits_text_plan(plan, usage)
                + "\n\nМожно докупить пакет на сегодня:",
                reply_markup=topup_kb(plan),
            )
        else:
            await update.message.reply_text(
                "🔒 Бесплатный лимит картинок на сегодня исчерпан (UTC).\n"
                + _limits_text_free(settings, usage)
                + "\n\nВыбери подписку:",
                reply_markup=plans_kb(settings),
            )
        return

    prompt = _extract_after_command(update.message.text)
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    try:
        img = generate_image_bytes(
            _enhance_image_prompt(prompt),
            model=settings.image_model,
            width=1024,
            height=1024,
            timeout=settings.request_timeout_sec,
            max_len=settings.max_prompt_len,
        )
        db.inc_img(user_id, today_utc())
        bio = io.BytesIO(img)
        bio.name = "image.png"
        await update.message.reply_photo(photo=bio, caption=f"🖼️ {prompt[:900]}")
    except Exception as e:
        logger.exception("Image generation failed")
        await update.message.reply_text(f"⚠️ Ошибка генерации картинки: {e}")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if text.startswith("/"):
        return

    # Quick-menu buttons (reply keyboard)
    if text == "⭐ Тарифы":
        await plans_cmd(update, context)
        return
    if text == "📊 Статус":
        await status_cmd(update, context)
        return
    if text == "🧠 Задать вопрос":
        context.user_data["mode"] = "ask"
        await update.message.reply_text("Ок! Задай вопрос — отвечу максимально понятно.")
        return
    if text == "📚 Домашка":
        context.user_data["mode"] = "homework"
        await update.message.reply_text("Пришли задачу (можно текстом). Я решу *пошагово*.", parse_mode="Markdown")
        return
    if text == "📝 Эссе/реферат":
        context.user_data["mode"] = "essay"
        await update.message.reply_text("Пришли тему и требования (объём, стиль). Я подготовлю план и текст.")
        return
    if text == "💻 Код":
        context.user_data["mode"] = "code"
        await update.message.reply_text("Опиши задачу по коду (язык/стек) или пришли ошибку — помогу и дам рабочий пример.")
        return
    if text == "🖼️ Картинка":
        context.user_data["mode"] = "image"
        await update.message.reply_text("Опиши картинку текстом (например: `кот в очках в стиле аниме`).", parse_mode="Markdown")
        return

    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    user_id = update.effective_user.id

    plan, paid_until = _get_subscription(db, settings, user_id)
    usage = db.get_daily_usage(user_id, today_utc())

    mode = (context.user_data.get("mode") or "ask").lower()

    # If user is in image mode, treat any message as image prompt
    is_img = (mode == "image") or _looks_like_image_request(text)

    if is_img:
        ok, _ = _can_use_img(settings, plan, paid_until, usage)
        if not ok:
            if plan and is_active(paid_until):
                await update.message.reply_text(
                    "🔒 Суточный лимит картинок исчерпан (UTC).\n"
                    + _limits_text_plan(plan, usage)
                    + "\n\nМожно докупить пакет на сегодня:",
                    reply_markup=topup_kb(plan),
                )
            else:
                await update.message.reply_text(
                    "🔒 Бесплатный лимит картинок на сегодня исчерпан (UTC).\n"
                    + _limits_text_free(settings, usage)
                    + "\n\nВыбери подписку:",
                    reply_markup=plans_kb(settings),
                )
            return

        prompt = _strip_image_prefix(text) if _looks_like_image_request(text) else text
        prompt = _enhance_image_prompt(prompt)

        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        try:
            img = generate_image_bytes(
                prompt,
                model=settings.image_model,
                width=1024,
                height=1024,
                timeout=settings.request_timeout_sec,
                max_len=settings.max_prompt_len,
            )
            db.inc_img(user_id, today_utc())
            bio = io.BytesIO(img)
            bio.name = "image.png"
            await update.message.reply_photo(photo=bio, caption=f"🖼️ {prompt[:900]}")
        except Exception as e:
            logger.exception("Image generation failed")
            await update.message.reply_text(f"⚠️ Ошибка генерации картинки: {e}")
        return

    # Text default
    ok, _ = _can_use_text(settings, plan, paid_until, usage)
    if not ok:
        if plan and is_active(paid_until):
            await update.message.reply_text(
                "🔒 Суточный лимит ответов исчерпан (UTC).\n"
                + _limits_text_plan(plan, usage)
                + "\n\nМожно докупить пакет на сегодня:",
                reply_markup=topup_kb(plan),
            )
        else:
            await update.message.reply_text(
                "🔒 Бесплатный лимит ответов на сегодня исчерпан (UTC).\n"
                + _limits_text_free(settings, usage)
                + "\n\nВыбери подписку:",
                reply_markup=plans_kb(settings),
            )
        return

    prompt = _build_text_prompt(text, mode)

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        answer = generate_text(_build_text_prompt(prompt, 'ask'), model=settings.text_model, timeout=settings.request_timeout_sec, max_len=settings.max_prompt_len)
        db.inc_text(user_id, today_utc())
    except Exception as e:
        logger.exception("Text generation failed")
        answer = f"⚠️ Ошибка генерации текста: {e}"
    await update.message.reply_text(answer)

async def renewal_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data["settings"]
    db: DB = context.application.bot_data["db"]
    try:
        expiring = db.get_expiring_within(settings.renew_reminder_days)
    except Exception:
        logger.exception("Failed to fetch expiring subscriptions")
        return

    for sub in expiring:
        user_id = sub["user_id"]
        plan = _plan_by_name(settings, sub.get("plan"))
        paid_until = sub.get("paid_until")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"⏳ Подписка {plan.name} скоро закончится: {paid_until.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                    f"Продлить на 30 дней за {plan.price_stars}⭐?"
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(f"Продлить {plan.name} ({plan.price_stars}⭐)", callback_data=f"BUY_{plan.name.upper()}")]]
                ),
            )
            db.set_last_reminder_day(user_id, today_utc())
        except Exception:
            # user may have blocked the bot; ignore
            logger.exception("Failed to send reminder to %s", user_id)

def main() -> None:
    settings = load_settings()
    db = DB(settings.database_url)
    db.init()

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["db"] = db

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plans", plans_cmd))
    app.add_handler(CommandHandler("buy", buy_cmd))
    app.add_handler(CommandHandler("topup", topup_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("text", text_cmd))
    app.add_handler(CommandHandler("img", img_cmd))

    app.add_handler(CallbackQueryHandler(cbq_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    # Run a reminder job every 12 hours (UTC-based checks inside)
    app.job_queue.run_repeating(renewal_reminder_job, interval=12 * 60 * 60, first=60)

    logger.info("Bot started.")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
