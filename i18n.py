def detect_lang(user_language_code: str | None, message_text: str | None) -> str:
    if user_language_code:
        lc = user_language_code.lower()
        if lc.startswith(("ru","uk","be","kk")):
            return "ru"
    if message_text:
        for ch in message_text:
            if "А" <= ch <= "я" or ch in "ёЁіІїЇєЄ":
                return "ru"
    return "en"

T = {
  "ru": {
    "welcome_title": "🎓 StudyAI — помощник для учёбы и креатива",
    "welcome_body": "Выбери режим ниже.\n\n💡 Совет: пригласи друга (Профиль → Рефералка) и получи бонус.",
    "menu_study": "📚 Помощь в учёбе / ДЗ",
    "menu_image": "🖼 Создать картинку",
    "menu_edit": "🧩 Изменить фото",
    "menu_chill": "🎧 Отвлечься",
    "menu_sub": "⭐ Подписка",
    "menu_topup": "🛒 Докупить",
    "menu_profile": "👤 Профиль",
    "menu_help": "ℹ️ Помощь",
    "ask_study": "Напиши вопрос или задание. Я отвечу как репетитор (пошагово).",
    "ask_image": "Напиши, что нарисовать (лучше коротко).",
    "ask_edit": "Отправь фото, затем напиши что изменить.",
    "chill_menu": "Выбери:",
    "chill_song": "🎵 Сгенерировать трек",
    "chill_fact": "😄 Случайный факт",
    "back": "⬅️ Назад",
    "need_sub_for_topup": "Докупить можно только при активной подписке (PRO/ULTRA).",
    "limit_reached_text": "🚫 Лимит ответов на сегодня закончился.",
    "limit_reached_img": "🚫 Лимит картинок на сегодня закончился.",
    "limit_reached_song": "🚫 Лимит треков на сегодня закончился.",
    "upsell": "⭐ Оформи PRO/ULTRA или докупи пакет — и продолжай сразу.",
    "profile": "👤 Профиль",
    "plan": "Тариф",
    "until": "До",
    "today": "Сегодня",
    "left": "Осталось",
    "ref_link": "🔗 Твоя реферальная ссылка",
    "ref_about": "Пригласи друга — получишь бонус, когда он впервые начнёт пользоваться ботом.",
    "payment_title_sub": "Подписка StudyAI",
    "payment_title_topup": "Покупка StudyAI",
    "paid_ok": "✅ Оплата получена! Начислил.",
    "error_generic": "Упс, что-то пошло не так. Попробуй ещё раз.",
    "hint_text_cmd": "Пример: /text Напиши доклад про красный фосфор",
    "help": "ℹ️ Как пользоваться:\n\n📚 Учёба: просто пиши задачу/вопрос.\n🖼 Картинка: опиши что хочешь.\n🎧 Отвлечься: трек.\n\n⭐ Подписка даёт большие лимиты.\n🛒 Докупить — если лимит закончился."
  },
  "en": {
    "welcome_title": "🎓 StudyAI — study & creativity assistant",
    "welcome_body": "Pick a mode below.\n\n💡 Tip: invite a friend (Profile → Referral) to get a bonus.",
    "menu_study": "📚 Study help / Homework",
    "menu_image": "🖼 Generate image",
    "menu_edit": "🧩 Edit photo",
    "menu_chill": "🎧 Chill",
    "menu_sub": "⭐ Subscription",
    "menu_topup": "🛒 Top up",
    "menu_profile": "👤 Profile",
    "menu_help": "ℹ️ Help",
    "ask_study": "Send your question/task. I’ll answer like a tutor (step-by-step).",
    "ask_image": "Describe the image you want (keep it short).",
    "ask_edit": "Send a photo, then tell what to change.",
    "chill_menu": "Choose:",
    "chill_song": "🎵 Generate track",
    "chill_fact": "😄 Random fact",
    "back": "⬅️ Back",
    "need_sub_for_topup": "Top-ups are available only with an active PRO/ULTRA subscription.",
    "limit_reached_text": "🚫 Daily answer limit reached.",
    "limit_reached_img": "🚫 Daily image limit reached.",
    "limit_reached_song": "🚫 Daily track limit reached.",
    "upsell": "⭐ Upgrade to PRO/ULTRA or buy a top-up to continue now.",
    "profile": "👤 Profile",
    "plan": "Plan",
    "until": "Until",
    "today": "Today",
    "left": "Left",
    "ref_link": "🔗 Your referral link",
    "ref_about": "Invite a friend — you get a bonus once they start using the bot.",
    "payment_title_sub": "StudyAI subscription",
    "payment_title_topup": "StudyAI purchase",
    "paid_ok": "✅ Payment received! Credited.",
    "error_generic": "Oops, something went wrong. Please try again.",
    "hint_text_cmd": "Example: /text Write a report about red phosphorus",
    "help": "ℹ️ How to use:\n\n📚 Study: send any task/question.\n🖼 Image: describe what you want.\n🎧 Chill: generate a track.\n\n⭐ Subscription increases daily limits.\n🛒 Top up — if you hit limits."
  }
}

def tr(lang: str, key: str) -> str:
    lang = lang if lang in T else "en"
    return T[lang].get(key, T["en"].get(key, key))
