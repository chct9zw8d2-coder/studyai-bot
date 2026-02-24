# StudyAI Telegram Bot (DeepSeek + Vision + Stability Images)

## What it does
- DeepSeek: text tutoring (homework, explanations, step-by-step)
- DeepSeek Vision: check homework from a photo (image upload)
- Telegram Stars: subscriptions + top-ups
- PostgreSQL: users, daily usage, payments, referrals, payouts

## Railway Variables
Required:
- TELEGRAM_BOT_TOKEN
- DATABASE_URL
- OWNER_USER_ID
- ADMIN_CHAT_ID

DeepSeek:
- DEEPSEEK_API_KEY
- DEEPSEEK_MODEL (default: deepseek-chat)
- DEEPSEEK_VISION_MODEL (required for photo checking)
- DEEPSEEK_BASE_URL (default: https://api.deepseek.com)

Stability (images):
- STABILITY_API_KEY
- STABILITY_ENDPOINT (default: https://api.stability.ai/v2beta/stable-image/generate/sd3)
- STABILITY_OUTPUT_FORMAT (default: png)

Stars / referrals:
- STARS_CURRENCY (default: XTR)
- REF_PERCENT (default: 0.30)
- MIN_PAYOUT_STARS (default: 300)

## Run
Railway uses Procfile. Locally:
```bash
pip install -r requirements.txt
python bot.py
```
