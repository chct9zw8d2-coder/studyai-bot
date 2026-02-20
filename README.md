# StudyAI Bot (Telegram)

## Env vars (Railway → Variables)
- `TELEGRAM_BOT_TOKEN` (или `BOT_TOKEN`)
- `DATABASE_URL` (Railway Postgres создаёт сам)

## Запуск локально
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="..."
export DATABASE_URL="postgresql://..."
python bot.py
```

## Команды
- `/start` — меню
- `/profile` — лимиты/подписка
- `/text <запрос>` — текст (но можно и просто написать текст после выбора меню)

## Тарифы
- FREE: 10 текстов/день, 2 картинки/день
- PRO: 499⭐ на 30 дней
- VIP: 999⭐ на 30 дней
- Докупка пакетов на сегодня: 199⭐
