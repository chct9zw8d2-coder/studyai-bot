
import uuid
import logging
from datetime import datetime, timezone, date

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, ContextTypes, filters
)

import db
import config
from ai.deepseek import generate_text
from ai.replicate_media import generate_image, edit_image, generate_music

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("studyai")

def _now_utc():
    return datetime.now(timezone.utc)

def _today_utc() -> date:
    return _now_utc().date()

def _is_sub_active(sub) -> bool:
    return bool(sub and sub.get("paid_until") and sub["paid_until"] > _now_utc())

def _limits_for_user(sub):
    if _is_sub_active(sub):
        plan = sub["plan"]
        p = config.PLANS.get(plan, config.PLANS["pro"])
        return p["text_per_day"], p["img_per_day"], p
    return config.FREE_TEXT_PER_DAY, config.FREE_IMG_PER_DAY, None

def _remaining(user_id: int, sub):
    usage = db.get_daily_usage(user_id, _today_utc())
    top = db.get_daily_topup(user_id, _today_utc())
    text_limit, img_limit, plan = _limits_for_user(sub)
    text_limit += top["text_bonus"]
    img_limit += top["img_bonus"]
    return {
        "text_left": max(0, text_limit - usage["text_used"]),
        "img_left": max(0, img_limit - usage["img_used"]),
        "text_limit": text_limit,
        "img_limit": img_limit,
        "text_used": usage["text_used"],
        "img_used": usage["img_used"],
        "plan": plan,
    }

def main_menu():
    kb = [
        [InlineKeyboardButton("📚 Помощь в учебе / ДЗ", callback_data="mode:study")],
        [InlineKeyboardButton("🎨 Создать картинку", callback_data="mode:image"),
         InlineKeyboardButton("🧩 Изменить фото", callback_data="mode:edit")],
        [InlineKeyboardButton("🎧 Отвлечься", callback_data="menu:fun")],
        [InlineKeyboardButton("⭐ Подписка", callback_data="menu:plans"),
         InlineKeyboardButton("🛒 Докупить", callback_data="menu:topup")],
        [InlineKeyboardButton("👤 Профиль / Лимиты", callback_data="menu:status"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="menu:help")],
    ]
    return InlineKeyboardMarkup(kb)

def fun_menu():
    kb = [
        [InlineKeyboardButton(f"🎵 Песня/музыка — {config.SONG_PRICE}⭐", callback_data="buy:song")],
        [InlineKeyboardButton("😄 Шуточный ответ", callback_data="mode:fun")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(kb)

def plans_menu(sub):
    lines = []
    for key, p in config.PLANS.items():
        lines.append(f"**{p['name']}** — {p['price']}⭐/мес\n• {p['text_per_day']} текстов/сутки\n• {p['img_per_day']} картинок/сутки")
    text = (
        "⭐ **Подписка StudyAI**\n\n"
        "Бесплатно:\n"
        f"• {config.FREE_TEXT_PER_DAY} текстов/сутки\n• {config.FREE_IMG_PER_DAY} картинок/сутки\n\n"
        + "\n\n".join(lines) +
        "\n\n⚠️ Telegram Stars не поддерживают автосписание без действия пользователя. "
        "Но продление — 1 клик, и бот напомнит заранее."
    )
    kb = [
        [InlineKeyboardButton("✅ Купить Basic", callback_data="buy:sub:basic")],
        [InlineKeyboardButton("🔥 Купить Pro", callback_data="buy:sub:pro")],
        [InlineKeyboardButton("👑 Купить Ultra", callback_data="buy:sub:ultra")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu:main")],
    ]
    return text, InlineKeyboardMarkup(kb)

def topup_menu(sub):
    if not _is_sub_active(sub):
        text = "🛒 Докупка доступна только при активной подписке (Basic/Pro/Ultra)."
        kb = [[InlineKeyboardButton("⭐ Подписка", callback_data="menu:plans")],
              [InlineKeyboardButton("🔙 Назад", callback_data="menu:main")]]
        return text, InlineKeyboardMarkup(kb)

    p = config.PLANS[sub["plan"]]
    text = (
        f"🛒 **Докупить пакет на сегодня (UTC)**\n\n"
        f"План: **{p['name']}**\n"
        f"Цена: **{p['topup_price']}⭐**\n"
        f"Добавит: **+{p['topup_text']} текстов** и **+{p['topup_img']} картинок** до конца суток (UTC).\n\n"
        "Можно покупать несколько раз в сутки."
    )
    kb = [
        [InlineKeyboardButton(f"Купить пакет ({p['topup_price']}⭐)", callback_data="buy:topup")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu:main")],
    ]
    return text, InlineKeyboardMarkup(kb)

def help_text():
    return (
        "ℹ️ **Как пользоваться**\n\n"
        "📚 *Помощь в учебе / ДЗ*: просто напиши вопрос, задачу или тему.\n"
        "🎨 *Создать картинку*: напиши, что нарисовать (например: «реалистичный кот в космосе»).\n"
        "🧩 *Изменить фото*: нажми кнопку, отправь фото, затем напиши, что изменить.\n"
        "🎧 *Отвлечься*: можно заказать песню/музыку за Stars.\n"
    )

def _order_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"

async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str, description: str, stars: int, payload: str):
    prices = [LabeledPrice(label=title, amount=stars)]
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=config.CURRENCY,
        prices=prices,
    )

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    order = db.get_order(payload)
    if not order:
        await update.message.reply_text("✅ Платёж получен. Спасибо!", reply_markup=main_menu())
        return

    db.mark_order_paid(payload)
    kind = order["kind"]
    data = order["payload"] or {}

    if kind.startswith("sub_"):
        plan = kind.split("_", 1)[1]
        until = db.add_subscription_days(user_id, plan, config.SUB_DAYS)
        await update.message.reply_text(
            f"✅ Подписка **{config.PLANS[plan]['name']}** активирована до **{until.date()}** (UTC).",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
        return

    if kind == "topup":
        sub = db.get_subscription(user_id)
        if not _is_sub_active(sub):
            await update.message.reply_text("Пакет можно купить только при активной подписке.", reply_markup=main_menu())
            return
        p = config.PLANS[sub["plan"]]
        db.add_daily_topup(user_id, p["topup_text"], p["topup_img"], _today_utc())
        await update.message.reply_text(
            f"✅ Добавлено +{p['topup_text']} текстов и +{p['topup_img']} картинок на сегодня (UTC).",
            reply_markup=main_menu(),
        )
        return

    if kind == "song":
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            await update.message.reply_text("✅ Платёж получен. Открой 🎧 Отвлечься и попробуй снова.", reply_markup=main_menu())
            return
        await update.message.reply_text("🎛 Генерирую музыку…")
        try:
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_AUDIO)
            url = generate_music(prompt, duration=config.SONG_DURATION)
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=url, caption="🎵 Готово!", reply_markup=main_menu())
        except Exception:
            log.exception("music failed")
            await update.message.reply_text("⚠️ Музыка временно недоступна. Попробуй позже.", reply_markup=main_menu())
        return

    await update.message.reply_text("✅ Платёж получен. Спасибо!", reply_markup=main_menu())

async def post_init(app: Application):
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.upsert_user(update.effective_user.id)
    db.set_state(update.effective_user.id, None, None)
    await update.message.reply_text(
        "👋 **StudyAI** — помощник для школы, колледжа и университета.\n\n"
        "Выбери режим и напиши запрос.",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id)
    sub = db.get_subscription(user_id)
    rem = _remaining(user_id, sub)
    plan_name = "Free"
    until = ""
    if _is_sub_active(sub):
        plan_name = config.PLANS[sub["plan"]]["name"]
        until = f"\nПодписка до: {sub['paid_until'].date()} (UTC)"
    text = (
        f"👤 **Профиль**\n\n"
        f"Тариф: **{plan_name}**{until}\n\n"
        f"Сегодня (UTC):\n"
        f"• Текст: {rem['text_used']} / {rem['text_limit']} (осталось {rem['text_left']})\n"
        f"• Картинки: {rem['img_used']} / {rem['img_limit']} (осталось {rem['img_left']})\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    db.upsert_user(user_id)
    data = q.data or ""

    if data == "menu:main":
        db.set_state(user_id, None, None)
        await q.edit_message_text("Главное меню:", reply_markup=main_menu())
        return
    if data == "menu:fun":
        db.set_state(user_id, None, None)
        await q.edit_message_text("🎧 Отвлечься:", reply_markup=fun_menu())
        return
    if data == "menu:help":
        await q.edit_message_text(help_text(), parse_mode="Markdown", reply_markup=main_menu())
        return
    if data == "menu:status":
        sub = db.get_subscription(user_id)
        rem = _remaining(user_id, sub)
        plan_name = "Free"
        until = ""
        if _is_sub_active(sub):
            plan_name = config.PLANS[sub["plan"]]["name"]
            until = f"\nПодписка до: {sub['paid_until'].date()} (UTC)"
        text = (
            f"👤 **Профиль**\n\n"
            f"Тариф: **{plan_name}**{until}\n\n"
            f"Сегодня (UTC):\n"
            f"• Текст: {rem['text_used']} / {rem['text_limit']} (осталось {rem['text_left']})\n"
            f"• Картинки: {rem['img_used']} / {rem['img_limit']} (осталось {rem['img_left']})\n"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
        return
    if data == "menu:plans":
        sub = db.get_subscription(user_id)
        text, kb = plans_menu(sub)
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        return
    if data == "menu:topup":
        sub = db.get_subscription(user_id)
        text, kb = topup_menu(sub)
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    if data.startswith("mode:"):
        mode = data.split(":", 1)[1]
        if mode in ("study", "image", "edit", "fun"):
            db.set_state(user_id, mode, None)
            msg = {
                "study": "📚 Напиши вопрос/задачу/тему для ДЗ.",
                "image": "🎨 Напиши, какую картинку создать.",
                "edit": "🧩 Отправь фото, затем напиши, что изменить.",
                "fun": "😄 Напиши, что хочешь — отвечу коротко и смешно."
            }[mode]
            await q.edit_message_text(msg, reply_markup=main_menu())
        return

    if data.startswith("buy:sub:"):
        plan = data.split(":")[-1]
        p = config.PLANS[plan]
        oid = _order_id(f"sub_{plan}")
        db.create_order(oid, user_id, f"sub_{plan}", {"plan": plan})
        await send_invoice(update, context, f"Подписка {p['name']} (30 дней)", f"{p['text_per_day']} текстов/сутки и {p['img_per_day']} картинок/сутки", p["price"], oid)
        return

    if data == "buy:topup":
        sub = db.get_subscription(user_id)
        if not _is_sub_active(sub):
            await q.edit_message_text("Докупить можно только при активной подписке.", reply_markup=main_menu())
            return
        p = config.PLANS[sub["plan"]]
        oid = _order_id("topup")
        db.create_order(oid, user_id, "topup", {"plan": sub["plan"], "day": str(_today_utc())})
        await send_invoice(update, context, f"Пакет на сегодня ({p['name']})", f"+{p['topup_text']} текстов и +{p['topup_img']} картинок на сутки (UTC)", p["topup_price"], oid)
        return

    if data == "buy:song":
        db.set_state(user_id, "song_prompt", None)
        await q.edit_message_text(
            f"🎵 Опиши песню/музыку (жанр, настроение, инструменты, тема).\n"
            f"После этого я отправлю счёт на {config.SONG_PRICE}⭐.",
            reply_markup=fun_menu()
        )
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id)
    txt = (update.message.text or "").strip()
    if not txt:
        return

    state, payload = db.get_state(user_id)
    sub = db.get_subscription(user_id)
    rem = _remaining(user_id, sub)

    if state == "song_prompt":
        oid = _order_id("song")
        db.create_order(oid, user_id, "song", {"prompt": txt})
        db.set_state(user_id, None, None)
        await update.message.reply_text("✅ Принято. Отправляю оплату…")
        await send_invoice(update, context, "Песня/музыка", "Генерация аудиофайла по твоему описанию", config.SONG_PRICE, oid)
        return

    mode = state or "study"

    if mode in ("study", "fun"):
        if rem["text_left"] <= 0:
            if _is_sub_active(sub):
                t, kb = topup_menu(sub)
                await update.message.reply_text("Лимит текста на сегодня закончился. Можно докупить пакет.", parse_mode="Markdown", reply_markup=kb)
            else:
                t, kb = plans_menu(sub)
                await update.message.reply_text("Лимит текста на сегодня закончился. Оформи подписку.", parse_mode="Markdown", reply_markup=kb)
            return
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        try:
            ans = generate_text(txt, mode=("fun" if mode == "fun" else "study"))
        except Exception:
            log.exception("deepseek failed")
            await update.message.reply_text("⚠️ Текстовый генератор временно недоступен. Попробуй позже.", reply_markup=main_menu())
            return
        db.inc_daily_usage(user_id, text_inc=1)
        await update.message.reply_text(ans, reply_markup=main_menu())
        return

    if mode == "image":
        if rem["img_left"] <= 0:
            if _is_sub_active(sub):
                t, kb = topup_menu(sub)
                await update.message.reply_text("Лимит картинок на сегодня закончился. Можно докупить пакет.", parse_mode="Markdown", reply_markup=kb)
            else:
                t, kb = plans_menu(sub)
                await update.message.reply_text("Лимит картинок на сегодня закончился. Оформи подписку.", parse_mode="Markdown", reply_markup=kb)
            return
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        try:
            prompt = f"realistic, high detail, sharp, photo, {txt}"
            url = generate_image(prompt)
            db.inc_daily_usage(user_id, img_inc=1)
            await update.message.reply_photo(photo=url, caption="🎨 Готово!", reply_markup=main_menu())
        except Exception:
            log.exception("image failed")
            await update.message.reply_text("⚠️ Генерация картинок временно недоступна. Попробуй позже.", reply_markup=main_menu())
        return

    if mode == "edit":
        if not payload or not payload.get("image_url"):
            await update.message.reply_text("Сначала отправь фото, потом напиши, что изменить 🙂", reply_markup=main_menu())
            return
        if rem["img_left"] <= 0:
            if _is_sub_active(sub):
                t, kb = topup_menu(sub)
                await update.message.reply_text("Лимит картинок на сегодня закончился. Можно докупить пакет.", parse_mode="Markdown", reply_markup=kb)
            else:
                t, kb = plans_menu(sub)
                await update.message.reply_text("Лимит картинок на сегодня закончился. Оформи подписку.", parse_mode="Markdown", reply_markup=kb)
            return
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_PHOTO)
        try:
            image_url = payload["image_url"]
            prompt = f"high quality, realistic edit: {txt}"
            url = edit_image(image_url, prompt, strength=0.6)
            db.inc_daily_usage(user_id, img_inc=1)
            db.set_state(user_id, "edit", {"image_url": image_url})
            await update.message.reply_photo(photo=url, caption="🧩 Готово!", reply_markup=main_menu())
        except Exception:
            log.exception("edit failed")
            await update.message.reply_text("⚠️ Редактирование временно недоступно. Попробуй позже.", reply_markup=main_menu())
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id)
    state, payload = db.get_state(user_id)
    if state != "edit":
        await update.message.reply_text("Чтобы изменить фото: нажми 🧩 «Изменить фото» в меню.", reply_markup=main_menu())
        return
    photo = update.message.photo[-1]
    f = await context.bot.get_file(photo.file_id)
    db.set_state(user_id, "edit", {"image_url": f.file_path})
    await update.message.reply_text("✅ Фото получено. Теперь напиши, что изменить.", reply_markup=main_menu())

def build_app() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app

def main():
    db.init_db()
    app = build_app()
    log.info("Bot started")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
