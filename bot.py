
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 Сгенерировать текст", callback_data="gen_text")],
        [InlineKeyboardButton("🎨 Сгенерировать картинку", callback_data="gen_image")],
        [InlineKeyboardButton("⭐ Подписка", callback_data="subscription")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Добро пожаловать в StudyAI!\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "gen_text":
        await query.edit_message_text("✍️ Напишите: /text ваш запрос")

    elif query.data == "gen_image":
        await query.edit_message_text("🎨 Напишите: /image ваш запрос")

    elif query.data == "subscription":
        await query.edit_message_text(
            "⭐ Подписка StudyAI\n\n"
            "Free — бесплатно\n"
            "Pro — 199⭐ / месяц\n"
            "Ultra — 399⭐ / месяц\n\n"
            "Оплата через Telegram Stars скоро будет подключена."
        )

async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /text Напиши идею поста")
        return

    prompt = " ".join(context.args)
    await update.message.reply_text(f"🧠 Генерация текста...\n\nЗапрос: {prompt}")

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /image Кот в космосе")
        return

    prompt = " ".join(context.args)
    await update.message.reply_text(f"🎨 Генерация изображения...\n\nЗапрос: {prompt}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("text", text_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
