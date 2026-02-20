import logging
from datetime import date

from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, PreCheckoutQueryHandler
)

import db
from config import TELEGRAM_BOT_TOKEN, PLANS, TOPUPS, CURRENCY, PROVIDER_TOKEN
from ai.deepseek import generate_text, DeepSeekError
from ai.pollinations import generate_image_bytes, PollinationsError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("studyai")

BTN_HOMEWORK = "📚 Помощь в учебе / ДЗ"
BTN_IMAGE    = "🖼 Картинка по тексту"
BTN_RELAX    = "🎧 Отвлечься (музыка)"
BTN_PROFILE  = "👤 Профиль/Лимиты"
BTN_SUB      = "⭐ Подписка"
BTN_BUY      = "🛒 Докупить"

MAIN_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_HOMEWORK), KeyboardButton(BTN_IMAGE)],
        [KeyboardButton(BTN_RELAX)],
        [KeyboardButton(BTN_PROFILE), KeyboardButton(BTN_SUB)],
        [KeyboardButton(BTN_BUY)],
    ],
    resize_keyboard=True
)

def _plan_caption(user_plan: str, active: bool) -> str:
    if user_plan == "free" or not active:
        return "Free"
    return f"{PLANS[user_plan]['name']} ✅"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id)
    await update.message.reply_text(
        "Привет! Я StudyAI 🙂\n\n"
        "📚 *Помощь в учебе / ДЗ* — быстрые ответы (DeepSeek)\n"
        "🖼 *Картинка по тексту* — реалистичные картинки (Pollinations)\n\n"
        "Выбери кнопку ниже 👇",
        reply_markup=MAIN_KB,
        parse_mode=ParseMode.MARKDOWN
    )

def _can_use(user_id: int, kind: str) -> tuple[bool, str]:
    today = date.today()
    plan_key, plan = db.get_limits(user_id)
    usage = db.get_usage(user_id, today)

    if kind == "text":
        limit = int(plan["text_per_day"])
        used = int(usage["text_used"])
        if used < limit:
            return True, ""
        if db.consume_topup(user_id, "text", 1):
            return True, ""
        return False, f"Лимит текста на сегодня исчерпан ({used}/{limit}). Нажми «{BTN_BUY}»."
    if kind == "img":
        limit = int(plan["img_per_day"])
        used = int(usage["img_used"])
        if used < limit:
            return True, ""
        if db.consume_topup(user_id, "img", 1):
            return True, ""
        return False, f"Лимит картинок на сегодня исчерпан ({used}/{limit}). Нажми «{BTN_BUY}»."
    return False, "Unknown kind"

def _add_usage(user_id: int, kind: str):
    db.add_usage(user_id, date.today(), kind, 1)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id)
    sub = db.get_subscription(user_id)
    _, plan = db.get_limits(user_id)
    usage = db.get_usage(user_id, date.today())
    cap = _plan_caption(sub["plan"], sub["active"])

    msg = (
        f"👤 *Профиль*\n"
        f"Тариф: *{cap}*\n\n"
        f"📚 Текст сегодня: *{usage['text_used']} / {plan['text_per_day']}*\n"
        f"🖼 Картинки сегодня: *{usage['img_used']} / {plan['img_per_day']}*\n\n"
        f"Лимиты считаются *за сутки*."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=MAIN_KB)

def _invoice_payload(kind: str, key: str) -> str:
    return f"{kind}:{key}"

async def show_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = []
    for k in ("basic","pro","ultra"):
        p = PLANS[k]
        kb.append([InlineKeyboardButton(f"{p['name']} — {p['price']}⭐ / 30 дней", callback_data=f"buy_sub:{k}")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_home")])
    await update.message.reply_text(
        "⭐ *Подписка (Stars)*\n\n"
        "Выбери тариф. Доступ откроется *сразу после оплаты*.\n"
        "Лимиты обновляются ежедневно.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_topups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = []
    for key, item in TOPUPS.items():
        kb.append([InlineKeyboardButton(f"{item['name']} — {item['price']}⭐", callback_data=f"buy_topup:{key}")])
    kb.append([InlineKeyboardButton("Назад", callback_data="back_home")])
    await update.message.reply_text(
        "🛒 *Докупить (Stars)*\n\n"
        "Покупки добавляются к лимитам и тратятся автоматически.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def cb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    if data == "back_home":
        await q.message.reply_text("Главное меню 👇", reply_markup=MAIN_KB)
        return

    if data.startswith("buy_sub:"):
        plan_key = data.split(":",1)[1]
        p = PLANS[plan_key]
        prices = [LabeledPrice(label=f"{p['name']} subscription", amount=int(p["price"]))]

        await q.message.reply_invoice(
            title=f"StudyAI {p['name']}",
            description=f"Подписка на 30 дней. Лимиты: {p['text_per_day']} текстов/день, {p['img_per_day']} картинок/день.",
            payload=_invoice_payload("sub", plan_key),
            provider_token=PROVIDER_TOKEN,
            currency=CURRENCY,
            prices=prices
        )
        return

    if data.startswith("buy_topup:"):
        key = data.split(":",1)[1]
        item = TOPUPS[key]
        prices = [LabeledPrice(label=item["name"], amount=int(item["price"]))]

        await q.message.reply_invoice(
            title=item["name"],
            description="Добавится на баланс лимитов и будет тратиться автоматически.",
            payload=_invoice_payload("topup", key),
            provider_token=PROVIDER_TOKEN,
            currency=CURRENCY,
            prices=prices
        )
        return

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.pre_checkout_query
    await q.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.upsert_user(user_id)
    payload = update.message.successful_payment.invoice_payload
    try:
        kind, key = payload.split(":", 1)
    except Exception:
        await update.message.reply_text("Оплата прошла, но я не смог распознать покупку. Напиши в поддержку.")
        return

    if kind == "sub":
        db.set_subscription(user_id, key)
        await update.message.reply_text(
            f"✅ Подписка *{PLANS[key]['name']}* активирована!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KB
        )
    elif kind == "topup":
        item = TOPUPS[key]
        db.add_topup(user_id, item["kind"], int(item["amount"]))
        await update.message.reply_text(
            f"✅ Куплено: *{item['name']}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KB
        )

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    db.upsert_user(user_id)

    if text == BTN_PROFILE:
        return await profile(update, context)
    if text == BTN_SUB:
        return await show_subscriptions(update, context)
    if text == BTN_BUY:
        return await show_topups(update, context)

    if text == BTN_HOMEWORK:
        context.user_data["mode"] = "text"
        await update.message.reply_text("Ок! Напиши вопрос по учебе одним сообщением 🙂", reply_markup=MAIN_KB)
        return
    if text == BTN_IMAGE:
        context.user_data["mode"] = "img"
        await update.message.reply_text("Ок! Напиши, какую картинку сделать (одним сообщением).", reply_markup=MAIN_KB)
        return
    if text == BTN_RELAX:
        context.user_data["mode"] = "song_text"
        await update.message.reply_text(
            "🎧 Сейчас я могу сделать *текст песни*.\n"
            "Аудиофайл подключим позже, когда добавишь API для музыки.\n\n"
            "Напиши жанр/настроение (например: «лоу‑фай для учебы»).",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KB
        )
        return

    mode = context.user_data.get("mode", "text")
    if mode == "img":
        return await handle_image(update, context)
    if mode == "song_text":
        return await handle_song_text(update, context)
    return await handle_text(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ok, msg = _can_use(user_id, "text")
    if not ok:
        await update.message.reply_text(msg, reply_markup=MAIN_KB)
        return

    prompt = update.message.text
    await update.message.reply_text("⏳ Думаю...", reply_markup=MAIN_KB)
    try:
        answer = await generate_text(
            prompt,
            system="Ты дружелюбный помощник для школьников и студентов. Отвечай кратко и понятно. Если нужен пошаговый разбор — делай пункты."
        )
    except DeepSeekError as e:
        await update.message.reply_text(f"Ошибка DeepSeek: {e}", reply_markup=MAIN_KB)
        return

    _add_usage(user_id, "text")
    await update.message.reply_text(answer[:4000], reply_markup=MAIN_KB)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ok, msg = _can_use(user_id, "img")
    if not ok:
        await update.message.reply_text(msg, reply_markup=MAIN_KB)
        return

    prompt = update.message.text
    await update.message.reply_text("🖼 Генерирую картинку...", reply_markup=MAIN_KB)
    try:
        img = await generate_image_bytes(prompt, width=1024, height=1024, model="flux")
    except PollinationsError as e:
        await update.message.reply_text(str(e), reply_markup=MAIN_KB)
        return

    _add_usage(user_id, "img")
    await update.message.reply_photo(photo=img, caption="Готово ✅", reply_markup=MAIN_KB)

async def handle_song_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ok, msg = _can_use(user_id, "text")
    if not ok:
        await update.message.reply_text(msg, reply_markup=MAIN_KB)
        return

    prompt = update.message.text.strip()
    await update.message.reply_text("🎶 Пишу текст песни...", reply_markup=MAIN_KB)
    try:
        answer = await generate_text(
            f"Сгенерируй короткий текст песни на русском (куплет+припев). Стиль/настроение: {prompt}. "
            "Сделай позитивно и без грубостей.",
            system="Ты автор песен. Пиши естественно."
        )
    except DeepSeekError as e:
        await update.message.reply_text(f"Ошибка DeepSeek: {e}", reply_markup=MAIN_KB)
        return

    _add_usage(user_id, "text")
    await update.message.reply_text(answer[:4000], reply_markup=MAIN_KB)

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty.")

    db.init_db()
    log.info("DB ready.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_router))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    log.info("Bot started.")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
