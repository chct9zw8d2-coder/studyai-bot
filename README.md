# StudyAI Bot (DeepSeek-chat + Replicate + Telegram Stars)

## Что умеет
- 📚 Помощь в учебе / ДЗ — DeepSeek-chat (быстро и дёшево)
- 🎨 Реалистичные картинки по тексту — Replicate (Flux Schnell)
- 🧩 Редактирование фото — Replicate img2img
- 🎵 Музыка/песня (аудиофайл) — Replicate MusicGen, 150⭐ за трек (работает без подписки)
- ⭐ Подписки: Basic/Pro/Ultra
- 🛒 Докупка пакета на сегодня — только при активной подписке

## Куда вставить токены (Railway → Variables)
- TELEGRAM_BOT_TOKEN = токен из @BotFather
- DATABASE_URL = из сервиса Postgres (Railway создаёт сам)
- DEEPSEEK_API_KEY = ключ DeepSeek
- REPLICATE_API_TOKEN = ключ Replicate

## Важно
Telegram Stars не поддерживают автосписание без действия пользователя. В боте это реализовано как 1‑клик продление (покупка снова).

## Деплой на Railway
1) New Project → GitHub Repository
2) Add Service → Database → PostgreSQL
3) В Variables бота добавить TELEGRAM_BOT_TOKEN, DATABASE_URL, DEEPSEEK_API_KEY, REPLICATE_API_TOKEN
4) Deploy / Redeploy
