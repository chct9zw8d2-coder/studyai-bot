import os
import logging

def startup_healthcheck():
    """Logs configuration readiness for Railway deployment."""
    required = [
        "TELEGRAM_BOT_TOKEN",
        "DATABASE_URL",
        "OWNER_USER_ID",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_VISION_MODEL",
        "STABILITY_API_KEY",
    ]
    optional = [
        "ADMIN_CHAT_ID",
        "DEEPSEEK_BASE_URL",
        "STARS_CURRENCY",
    ]

    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logging.error("❌ Missing required env vars: %s", ", ".join(missing))
    else:
        logging.info("✅ Required env vars: OK")

    present_opt = [k for k in optional if os.getenv(k)]
    logging.info("ℹ️ Optional env vars present: %s", ", ".join(present_opt) if present_opt else "none")

    # DB smoke test
    try:
        import db as _db
        _db.init_db()
        logging.info("✅ PostgreSQL: OK (init_db succeeded)")
    except Exception as e:
        logging.exception("❌ PostgreSQL: FAILED (%s)", e)

    # Stars note
    currency = os.getenv("STARS_CURRENCY", "XTR")
    logging.info("⭐ Stars currency: %s (BotFather must enable Telegram Stars payments)", currency)


import datetime as dt
from uuid import uuid4
import random
import hashlib

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, ContextTypes, filters
)

import db
from config import (
    TELEGRAM_BOT_TOKEN, PLANS, TOPUPS, STARS_CURRENCY,
    OWNER_USER_ID, ADMIN_CHAT_ID, MIN_PAYOUT_STARS, REVENUE_DAYS_DEFAULT,
    STABILITY_API_KEY, STABILITY_ENDPOINT,
    DEEPSEEK_MODEL, DEEPSEEK_MODEL_FREE, MAX_TOKENS,
    ENABLE_TEXT_CACHE, ENABLE_IMAGE_CACHE, TEXT_CACHE_TTL_DAYS, IMAGE_CACHE_TTL_DAYS,
)
from i18n import detect_lang, tr
from ai.deepseek import generate_text, generate_vision
from ai.stability_image import generate_image_bytes
from security.anti_abuse import check_rate_limit, is_duplicate_burst, clamp_text
from monetization.smart_paywall import PAYWALL_TRIGGER_COUNT, paywall_keyboard, paywall_keyboard_full, paywall_message_early, paywall_message_soft, paywall_message_limit, paywall_trigger_count_for_user
from monetization.personal_offers import choose_offer, build_offer_text, offer_keyboard, promo_expires_at, PROMO_BONUSES
from monetization.behavior_offers import focus_to_text

from monetization.ab_test import choose_variant
from monetization.first_purchase_bonus import bonus_offer_text, bonus_payload
from monetization.experiments import start_price_for_user, paywall_text_for_user, week_deal_for_user, recommend_plan_for_user, paywall_trigger_for_user



def full_breakdown_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Полный разбор", callback_data="action:expand")],
    ])

def make_cache_key(prefix: str, *parts: str) -> str:
    raw = "|".join([p.strip() for p in parts if p is not None])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def is_owner(user_id: int) -> bool:
    return OWNER_USER_ID and user_id == OWNER_USER_ID

def is_admin(user_id: int) -> bool:
    return user_id in (ADMIN_CHAT_ID, OWNER_USER_ID) and user_id != 0

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if "lang" in context.user_data:
        return context.user_data["lang"]
    lang = detect_lang(getattr(update.effective_user, "language_code", None),
                       getattr(update.effective_message, "text", None))
    context.user_data["lang"] = lang
    return lang


def maybe_personal_offer(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_key: str):
    """Show a personalized upgrade offer occasionally, and set a short-lived promo bonus."""
    uid = update.effective_user.id
    if is_owner(uid):
        return
    # don't spam
    last_ts = context.user_data.get("last_offer_ts")
    now = dt.datetime.utcnow()
    if last_ts and (now - last_ts).total_seconds() < 6 * 3600:
        return

    usage = db.get_usage(uid)
    focus = db.get_top_focus(uid)
    focus_text = focus_to_text(focus)
    text_used = int(usage.get("text_used", 0) or 0)
    img_used = int(usage.get("img_used", 0) or 0)

    plan = PLANS.get(plan_key, PLANS.get("free"))
    daily_text = int(plan.get("daily_text", 0) or 0)
    daily_img = int(plan.get("daily_img", 0) or 0)

    promo_kind, target_plan = choose_offer(plan_key, text_used, img_used, daily_text, daily_img)
    if not promo_kind:
        return

    # if a promo is already active, avoid overwriting too often
    active = db.get_active_promo(uid)
    if active:
        return

    expires = promo_expires_at()
    db.set_promo(uid, promo_kind, target_plan, expires)
    context.user_data["last_offer_ts"] = now

    lang = get_lang(update, context)
    text = build_offer_text(lang, promo_kind, target_plan, focus_text=focus_text)
    try:
        # use message context: if called from callback, fall back
        if getattr(update, "message", None):
            return update.message.reply_text(text, reply_markup=offer_keyboard())
    except Exception:
        pass


def referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref{user_id}"

def main_menu(lang: str, user_id: int = 0):
    buttons = [
        [InlineKeyboardButton(tr(lang,"menu_study"), callback_data="mode:study")],
        [InlineKeyboardButton(tr(lang,"menu_ege"), callback_data="mode:ege")],
        [InlineKeyboardButton(tr(lang,"menu_image"), callback_data="mode:image")],
        [InlineKeyboardButton(tr(lang,"menu_chill"), callback_data="menu:chill")],
        [InlineKeyboardButton(tr(lang,"menu_sub"),   callback_data="menu:sub")],
        [InlineKeyboardButton(tr(lang,"menu_topup"), callback_data="menu:topup")],
        [InlineKeyboardButton(tr(lang,"menu_profile"), callback_data="menu:profile")],
        [InlineKeyboardButton(tr(lang,"menu_ref"), callback_data="menu:ref")],
        [InlineKeyboardButton(tr(lang,"menu_help"), callback_data="menu:help")],
    ]
    if is_admin(user_id):
        buttons.insert(0, [InlineKeyboardButton(tr(lang,"menu_admin"), callback_data="menu:admin")])
    return InlineKeyboardMarkup(buttons)

def chill_menu(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang,"chill_fact"), callback_data="chill:fact")],
        [InlineKeyboardButton(tr(lang,"chill_riddle"), callback_data="chill:riddle")],
        [InlineKeyboardButton(tr(lang,"chill_quiz"), callback_data="chill:quiz")],
        [InlineKeyboardButton(tr(lang,"chill_mental"), callback_data="chill:mental")],
        [InlineKeyboardButton(tr(lang,"chill_word"), callback_data="chill:word")],
        [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:main")],
    ])

# --- OGE/EGE UI (exam + subject + actions) ---

SUBJECTS = [
    ("math", "Математика"),
    ("russian", "Русский"),
    ("informatics", "Информатика"),
    ("english", "Английский"),
    ("social", "Обществознание"),
    ("physics", "Физика"),
    ("chemistry", "Химия"),
    ("biology", "Биология"),
    ("history", "История"),
    ("geography", "География"),
    ("literature", "Литература"),
]

def subject_label(code: str) -> str:
    for c, label in SUBJECTS:
        if c == code:
            return label
    return code

def exam_menu(lang: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ОГЭ", callback_data="exam:oge"),
            InlineKeyboardButton("ЕГЭ", callback_data="exam:ege"),
        ],
        [InlineKeyboardButton(tr(lang, "back"), callback_data="menu:main")],
    ])

def subject_menu(lang: str, exam: str):
    buttons = []
    for code, label in SUBJECTS:
        buttons.append([InlineKeyboardButton(label, callback_data=f"subject:{exam}:{code}")])
    buttons.append([InlineKeyboardButton(tr(lang, "back"), callback_data="mode:ege")])
    return InlineKeyboardMarkup(buttons)

def ege_actions_menu(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Теория", callback_data="ege_action:theory")],
        [InlineKeyboardButton("✏️ Практика", callback_data="ege_action:practice")],
        [InlineKeyboardButton("🧪 Тест", callback_data="ege_action:test")],
        [InlineKeyboardButton("✅ Проверить ответ", callback_data="ege_action:check")],
        [InlineKeyboardButton("📊 Разбор", callback_data="ege_action:analysis")],
        [InlineKeyboardButton("← сменить предмет", callback_data="mode:ege")],
    ])

def sub_menu(lang: str, uid: int | None = None):
    buttons = []

    # Determine which plan to highlight as recommended (A/B)
    rec_winner = db.get_experiment_winner("recommend_plan")
    _, rec_plan = recommend_plan_for_user(uid or 0, winner=rec_winner)

    # First purchase special (if eligible)
    if uid is not None and db.first_purchase_eligible(uid):
        p = PLANS["start_first"]
        label = f"{p['name'][lang]} — {p['price_stars']}⭐"
        if rec_plan == "start":
            label += " ✅ Рекомендуем"
        buttons.append([InlineKeyboardButton(label, callback_data="buy:sub:start_first")])

    # START price A/B (unless discounted first purchase is shown above)
    price_winner = db.get_experiment_winner("start_price")
    var, price = start_price_for_user(uid or 0, winner=price_winner)
    p = dict(PLANS["start"])
    p["price_stars"] = price
    label = f"{p['name'][lang]} — {p['price_stars']}⭐"
    if rec_plan == "start":
        label += " ✅ Рекомендуем"
    buttons.append([InlineKeyboardButton(label, callback_data=f"buy:sub:start:{var}")])

    for k in ("pro", "ultra"):
        p = PLANS[k]
        label = f"{p['name'][lang]} — {p['price_stars']}⭐"
        if rec_plan == k:
            label += " ✅ Рекомендуем"
        buttons.append([InlineKeyboardButton(label, callback_data=f"buy:sub:{k}")])

    buttons.append([InlineKeyboardButton(tr(lang, "back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)



def topup_menu(lang: str, uid: int | None = None):
    buttons = []
    for key, item in (sorted(TOPUPS.items(), key=lambda kv: (0 if kv[0] == "week_pack" else 1, kv[0]))):
        if key == "week_pack":
            winner = db.get_experiment_winner("week_deal")
            var, deal = week_deal_for_user(uid or 0, winner=winner)
            try:
                db.log_offer_event(uid or 0, "impression", "week_deal", var)
            except Exception:
                pass
            title = deal["title"][lang]
            stars = deal["stars"]
        else:
            title = item["title"][lang]
            stars = item["stars"]
        buttons.append([InlineKeyboardButton(f"{title} — {stars}⭐", callback_data=f"buy:topup:{key}")])

    buttons.append([InlineKeyboardButton(tr(lang, "back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    inviter_id = None
    if context.args and context.args[0].startswith("ref"):
        try:
            inviter_id = int(context.args[0].replace("ref",""))
            if inviter_id == update.effective_user.id:
                inviter_id = None
        except Exception:
            inviter_id = None
    db.upsert_user(update.effective_user.id, lang=lang, inviter_id=inviter_id)
    await update.message.reply_text(
        f"<b>{tr(lang,'welcome_title')}</b>\\n\\n{tr(lang,'welcome_body')}",
        reply_markup=main_menu(lang, update.effective_user.id),
        parse_mode=ParseMode.HTML
    )

# Admin: revenue report
async def revenue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    lang = get_lang(update, context)
    days = REVENUE_DAYS_DEFAULT
    if context.args:
        try:
            days = max(1, min(365, int(context.args[0])))
        except Exception:
            days = REVENUE_DAYS_DEFAULT
    total, by_day, by_kind = db.revenue_summary(days=days)
    lines = [f"{tr(lang,'revenue')} ({days}d): <b>{total}⭐</b>", "", "<b>By kind</b>:"]
    for r in by_kind:
        lines.append(f"- {r['kind']}: {int(r['stars'])}⭐")
    lines.append("")
    lines.append("<b>By day</b>:")
    for r in by_day[:10]:
        lines.append(f"- {r['day']}: {int(r['stars'])}⭐")
    await update.message.reply_text("\\n".join(lines), parse_mode=ParseMode.HTML)

# Admin: list new payout requests
async def payouts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    lang = get_lang(update, context)
    rows = db.list_new_payouts(limit=10)
    if not rows:
        await update.message.reply_text("No new payout requests.")
        return
    await update.message.reply_text(tr(lang,"admin_payout_list"))
    for r in rows:
        pid = r["id"]
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Paid", callback_data=f"admin:payout:paid:{pid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin:payout:reject:{pid}")
        ]])
        await update.message.reply_text(
            f"ID: {pid}\\nUser: {r['user_id']}\\nAmount: {r['amount']}⭐",
            reply_markup=kb
        )

# User: create payout request
async def payout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    uid = update.effective_user.id
    if is_owner(uid):
        await update.message.reply_text("✅ Owner mode: unlimited & free. Payout not needed.")
        return
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text(tr(lang,"error_generic")); return

    amount = None
    if context.args:
        try: amount = int(context.args[0])
        except Exception: amount = None

    if amount is None:
        history = db.list_user_payouts(uid, limit=5)
        hist_lines = []
        for h in history:
            note = f" — {h['admin_note']}" if h.get("admin_note") else ""
            hist_lines.append(f"#{h['id']} — {h['amount']}⭐ — {h['status']}{note}")
        if not hist_lines:
            hist_lines = ["-"]
        await update.message.reply_text(
            f"{tr(lang,'payout_hint')}\\n{tr(lang,'ref_balance')}: {user['ref_balance']}⭐\\n\\n{tr(lang,'payout_history')}:\\n" + "\\n".join(hist_lines)
        )
        return

    ok, code = db.can_request_payout(uid)
    if not ok:
        if code=="too_small":
            await update.message.reply_text(tr(lang,"payout_too_small")+f" (min {MIN_PAYOUT_STARS}⭐)")
        elif code=="cooldown":
            await update.message.reply_text(tr(lang,"payout_cooldown"))
        else:
            await update.message.reply_text(tr(lang,"error_generic"))
        return

    if amount < MIN_PAYOUT_STARS:
        await update.message.reply_text(tr(lang,"payout_too_small")+f" (min {MIN_PAYOUT_STARS}⭐)"); return
    if user["ref_balance"] < amount:
        await update.message.reply_text(tr(lang,"payout_not_enough")); return

    try:
        pid = db.create_payout_request(uid, amount)
    except Exception:
        await update.message.reply_text(tr(lang,"error_generic")); return

    await update.message.reply_text(tr(lang,"payout_created"))
    if ADMIN_CHAT_ID:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Paid", callback_data=f"admin:payout:paid:{pid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin:payout:reject:{pid}")
        ]])
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"{tr(lang,'admin_payout_new')}\\nID: {pid}\\nUser: {uid}\\nAmount: {amount}⭐",
            reply_markup=kb
        )

async def text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /text Explain photosynthesis step-by-step"); return
    context.user_data["mode"]="study"
    await handle_study(update, context, " ".join(context.args).strip())

async def skip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("pending_reject_pid"):
        pid = context.user_data.pop("pending_reject_pid")
        db.reject_payout(pid, note="Rejected by admin")
        await update.message.reply_text("Skipped. Rejected.")
    else:
        await update.message.reply_text("Nothing to skip.")

        if not is_owner(uid):
            plan_key, *_ = db.remaining_today(uid)
            if plan_key == "free":
                await query.answer()
                await query.message.reply_text("Полный разбор доступен по подписке.", reply_markup=paywall_keyboard())
                return

        await query.answer()
        await query.message.reply_text("Готовлю полный разбор…")

        plan_key = "ultra"
        if not is_owner(uid):
            plan_key, *_ = db.remaining_today(uid)

        max_tokens = MAX_TOKENS.get(plan_key, 1400)
        model = DEEPSEEK_MODEL

        system = "You are StudyAI. Provide a very detailed step-by-step breakdown with clear explanations and checks. Do not reveal hidden chain-of-thought. Language must match the user's language."
        prompt = f"Сделай ПОЛНЫЙ разбор и объяснение.\n\n{last_prompt}"

        cache_key = make_cache_key("text", f"mode=expand:{last_mode}", f"lang={lang}", prompt)
        if ENABLE_TEXT_CACHE and not is_owner(uid):
            row = db.get_text_cache(cache_key, ttl_days=TEXT_CACHE_TTL_DAYS)
            if row and row.get("response"):
                await query.message.reply_text(row["response"])
                return

        try:
            reply = generate_text(prompt, system=system, max_tokens=max_tokens, model=model)
        except Exception:
            reply = tr(lang, "error_generic")

        if ENABLE_TEXT_CACHE and not is_owner(uid) and reply and "⚠️" not in reply:
            db.set_text_cache(cache_key, reply, model=model)

        await query.message.reply_text(reply)
        return

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = get_lang(update, context)
    data = q.data


    # Full breakdown on demand (two-level answers)
    if data == "action:expand":
        uid = q.from_user.id

        last_prompt = context.user_data.get("last_prompt")
        last_mode = context.user_data.get("last_mode", "study")

        if not last_prompt:
            await q.answer("Нет запроса для разбора.")
            return

        if not is_owner(uid):
            plan_key, *_ = db.remaining_today(uid)
            if plan_key == "free":
                await q.answer()
                await q.message.reply_text("Полный разбор доступен по подписке.", reply_markup=paywall_keyboard())
                return

        await q.answer()
        await q.message.reply_text("Готовлю полный разбор…")

        plan_key = "ultra"
        if not is_owner(uid):
            plan_key, *_ = db.remaining_today(uid)

        max_tokens = MAX_TOKENS.get(plan_key, 1400)
        model = DEEPSEEK_MODEL

        system = "You are StudyAI. Provide a very detailed step-by-step breakdown with clear explanations and checks. Do not reveal hidden chain-of-thought. Language must match the user's language."
        expand_prompt = f"Сделай ПОЛНЫЙ разбор и объяснение.\n\n{last_prompt}"

        cache_key = make_cache_key("text", f"mode=expand:{last_mode}", f"lang={lang}", expand_prompt)
        if ENABLE_TEXT_CACHE and not is_owner(uid):
            row = db.get_text_cache(cache_key, ttl_days=TEXT_CACHE_TTL_DAYS)
            if row and row.get("response"):
                await q.message.reply_text(row["response"])
                return

        try:
            reply = generate_text(expand_prompt, system=system, max_tokens=max_tokens, model=model)
        except Exception:
            reply = tr(lang, "error_generic")

        if ENABLE_TEXT_CACHE and not is_owner(uid) and reply and "⚠️" not in reply:
            db.set_text_cache(cache_key, reply, model=model)

        await q.message.reply_text(reply)
        return

    # --- OGE/EGE flow ---
    if data.startswith("exam:"):
        exam = data.split(":", 1)[1]
        context.user_data["exam"] = exam
        await q.edit_message_text(
            f"Выбери предмет для {exam.upper()}:",
            reply_markup=subject_menu(lang, exam)
        )
        return

    if data.startswith("subject:"):
        _, exam, subject = data.split(":", 2)
        context.user_data["exam"] = exam
        context.user_data["subject"] = subject
        await q.edit_message_text(
            f"{exam.upper()} • {subject_label(subject)}\n\nВыбери режим:",
            reply_markup=ege_actions_menu(lang)
        )
        return

    if data.startswith("ege_action:"):
        action = data.split(":", 1)[1]
        exam = context.user_data.get("exam", "ege")
        subject = context.user_data.get("subject")
        if not subject:
            await q.answer("Сначала выбери предмет")
            return

        subject_human = subject_label(subject)
        prompts = {
            "theory": f"Дай краткую, но понятную теорию для подготовки к {exam.upper()} по предмету {subject_human}.",
            "practice": f"Дай практические задания (разного типа) для подготовки к {exam.upper()} по предмету {subject_human}.",
            "test": f"Составь мини-тест (10 вопросов) для подготовки к {exam.upper()} по предмету {subject_human}.",
            "check": f"Я пришлю решение/ответ. Проверь и объясни ошибки. Контекст: {exam.upper()} по предмету {subject_human}.",
            "analysis": f"Сделай разбор типовых заданий и частых ошибок для {exam.upper()} по предмету {subject_human}.",
        }
        prompt = prompts.get(action)
        if not prompt:
            await q.answer("Неизвестное действие")
            return

        await q.message.reply_text("Генерирую…")
        await handle_ege(update, context, prompt)
        return

    if data.startswith("admin:payout:"):
        if not is_admin(q.from_user.id):
            await q.edit_message_text("Not allowed."); return
        _, _, action, pid_s = data.split(":", 3)
        pid = int(pid_s)
        req = db.get_payout(pid)
        if not req:
            await q.edit_message_text("Not found."); return

        if action=="paid":
            ok = db.approve_payout(pid)
            await q.edit_message_text(tr(lang,"admin_payout_paid") if ok else "Already processed.")
            try:
                await context.bot.send_message(chat_id=int(req["user_id"]), text=tr(lang,"user_payout_paid"))
            except Exception:
                pass
        else:
            context.user_data["pending_reject_pid"] = pid
            await q.edit_message_text(tr(lang,"admin_reject_ask"))
        return

    if data=="menu:main":
        await q.edit_message_text(tr(lang,"welcome_body"), reply_markup=main_menu(lang, update.effective_user.id)); return
    if data.startswith("mode:"):
        mode = data.split(":",1)[1]
        context.user_data["mode"]=mode
        if mode=="ege":
            await q.edit_message_text("Выбери экзамен:", reply_markup=exam_menu(lang))
        else:
            await q.edit_message_text(
                tr(lang,"ask_study") if mode=="study" else tr(lang,"ask_image"),
                reply_markup=main_menu(lang, update.effective_user.id)
            )
        return
    if data=="menu:chill":
        await q.edit_message_text(tr(lang,"chill_menu"), reply_markup=chill_menu(lang)); return
    if data=="menu:sub":
        await q.edit_message_text("⭐", reply_markup=sub_menu(lang, uid)); return
    if data=="menu:topup":
        await q.edit_message_text("🛒", reply_markup=topup_menu(lang, uid)); return
    if data=="menu:help":
        await q.edit_message_text(tr(lang,"help"), reply_markup=main_menu(lang, update.effective_user.id)); return
    if data=="menu:profile":
        await send_profile(q, context, lang); return
    if data=="menu:ref":
        await send_ref(q, context, lang); return

    
    
    if data=="chill:riddle":
        riddles = [
            ("Что можно увидеть с закрытыми глазами?", "Сон."),
            ("Без рук, без ног, а ворота открывает. Кто это?", "Ветер."),
            ("Что всегда перед тобой, но увидеть нельзя?", "Будущее."),
            ("Чем больше из неё берёшь, тем больше она становится. Что это?", "Яма."),
        ]
        qst, ans = random.choice(riddles)
        context.user_data["chill_answer"] = ans
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr(lang,"chill_show_answer"), callback_data="chill:show")],
            [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:chill")]
        ])
        await q.edit_message_text("🧠 Загадка:\n\n"+qst+"\n\nОтвет спрятан 😉", reply_markup=kb)
        return

    if data=="chill:quiz":
        quizzes = [
            ("Правда или ложь: у осьминога три сердца.", "Правда ✅"),
            ("Правда или ложь: бананы — это ягоды.", "Правда ✅"),
            ("Правда или ложь: золото можно есть.", "Да, в виде пищевого золота (E175) в микродозах. ✅"),
        ]
        qst, ans = random.choice(quizzes)
        context.user_data["chill_answer"] = ans
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr(lang,"chill_show_answer"), callback_data="chill:show")],
            [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:chill")]
        ])
        await q.edit_message_text("❓ Викторина:\n\n"+qst+"\n\nОтвет спрятан 😉", reply_markup=kb)
        return

    if data=="chill:mental":
        a = random.randint(12, 99)
        b = random.randint(12, 99)
        op = random.choice(["+", "-", "*"])
        if op == "-":
            a, b = max(a,b), min(a,b)
        expr = f"{a} {op} {b}"
        ans = str(eval(expr))
        context.user_data["game"] = "mental"
        context.user_data["game_answer"] = ans
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr(lang,"chill_show_answer"), callback_data="chill:show")],
            [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:chill")]
        ])
        await q.edit_message_text(
            f"➕ Устный счёт:\n\nСколько будет: <b>{expr}</b> ?\n\nНапиши ответ сообщением.",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        return

    if data=="chill:word":
        words = ["алгебра", "геометрия", "производная", "информатика", "вероятность", "литература", "химия", "биология"]
        word = random.choice(words)
        scrambled = "".join(random.sample(word, len(word)))
        context.user_data["game"] = "word"
        context.user_data["game_answer"] = word
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(tr(lang,"chill_show_answer"), callback_data="chill:show")],
            [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:chill")]
        ])
        await q.edit_message_text(
            f"🔤 Угадай слово:\n\nПеремешанное слово: <b>{scrambled}</b>\n\nНапиши правильное слово сообщением.",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
        return

    if data=="chill:show":
        ans = context.user_data.get("chill_answer") or context.user_data.get("game_answer") or "—"
        await q.answer(ans, show_alert=True)
        return

    if data=="menu:admin":
        if not is_admin(q.from_user.id):
            await q.edit_message_text("Not allowed.")
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Дашборд", callback_data="admin:dash")],
            [InlineKeyboardButton("💰 Revenue (7d)", callback_data="admin:revenue:7")],
            [InlineKeyboardButton("📋 Новые выплаты", callback_data="admin:payouts")],
            [InlineKeyboardButton(tr(lang,"back"), callback_data="menu:main")],
        ])
        await q.edit_message_text("🛠 Админ-панель:", reply_markup=kb)
        return

    if data=="admin:dash":
        if not is_admin(q.from_user.id):
            await q.edit_message_text("Not allowed.")
            return
        s = db.admin_summary()
        msg = (
            "📊 Дашборд\n\n"
            f"👥 Всего пользователей: <b>{s['total_users']}</b>\n"
            f"✅ Активных сегодня: <b>{s['active_today']}</b>\n"
            f"💬 Текст-запросов сегодня: <b>{s['text_used']}</b>\n"
            f"🖼 Картинок сегодня: <b>{s['img_used']}</b>"
        )
        await q.edit_message_text(
            msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang,"back"), callback_data="menu:admin")]])
        )
        return

    if data.startswith("admin:revenue:"):
        if not is_admin(q.from_user.id):
            await q.edit_message_text("Not allowed.")
            return
        try:
            days = int(data.split(":")[2])
        except Exception:
            days = REVENUE_DAYS_DEFAULT
        total, by_day, by_kind = db.revenue_summary(days=days)
        lines = [f"{tr(lang,'revenue')} ({days}d): <b>{total}⭐</b>", "", "<b>By kind</b>:"]
        for r in by_kind:
            lines.append(f"- {r['kind']}: {int(r['stars'])}⭐")
        lines.append("")
        lines.append("<b>By day</b>:")
        for r in by_day[:10]:
            lines.append(f"- {r['day']}: {int(r['stars'])}⭐")
        await q.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang,"back"), callback_data="menu:admin")]])
        )
        return

    if data=="admin:payouts":
        if not is_admin(q.from_user.id):
            await q.edit_message_text("Not allowed.")
            return
        rows = db.list_new_payouts(limit=10)
        if not rows:
            await q.edit_message_text(
                "No new payout requests.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang,"back"), callback_data="menu:admin")]])
            )
            return
        await q.edit_message_text(
            tr(lang,"admin_payout_list"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang,"back"), callback_data="menu:admin")]])
        )
        for r in rows:
            pid = r["id"]
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Paid", callback_data=f"admin:payout:paid:{pid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin:payout:reject:{pid}")
            ]])
            await q.message.reply_text(
                f"ID: {pid}\nUser: {r['user_id']}\nAmount: {r['amount']}⭐",
                reply_markup=kb
            )
        return
    if data=="chill:fact":
        fact = generate_text("Give one short surprising fact (1 sentence).", system="You are a fun fact generator.")
        await q.edit_message_text("😄 "+fact, reply_markup=chill_menu(lang)); return

    if data.startswith("buy:sub:"):
        await send_invoice_subscription(q, context, data.split(":")[2], lang); return
    if data.startswith("buy:topup:"):
        await send_invoice_topup(q, context, data.split(":")[2], lang); return

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not is_admin(update.effective_user.id):
        return False
    pid = context.user_data.get("pending_reject_pid")
    if not pid:
        return False
    note = update.message.text.strip()
    context.user_data.pop("pending_reject_pid", None)
    req = db.get_payout(int(pid))
    db.reject_payout(int(pid), note=note[:500])
    await update.message.reply_text(tr(get_lang(update, context),"admin_reject_done"))
    try:
        msg = tr(get_lang(update, context),"user_payout_rejected") + f"\\nПричина: {note[:500]}"
        await context.bot.send_message(chat_id=int(req["user_id"]), text=msg)
    except Exception:
        pass
    return True

async def send_profile(q, context, lang: str):
    uid = q.from_user.id
    user = db.get_user(uid)
    if not user:
        await q.edit_message_text(tr(lang,"error_generic"), reply_markup=main_menu(lang, update.effective_user.id)); return
    if is_owner(uid):
        msg = f"<b>{tr(lang,'profile')}</b>\\n{tr(lang,'plan')}: <b>OWNER</b>\\n{tr(lang,'today')}:\\n— text: ∞\\n— img: ∞"
        await q.edit_message_text(msg, reply_markup=main_menu(lang, update.effective_user.id), parse_mode=ParseMode.HTML); return

    plan, p, text_left, img_left, _, _ = db.remaining_today(uid)
    sub_until = user.get("sub_until")
    sub_str = sub_until.strftime("%Y-%m-%d") if sub_until else "-"
    msg = (
        f"<b>{tr(lang,'profile')}</b>\\n"
        f"{tr(lang,'plan')}: <b>{plan.upper()}</b>\\n"
        f"{tr(lang,'until')}: {sub_str}\\n\\n"
        f"{tr(lang,'today')}:\\n"
        f"— text: {tr(lang,'left')} {text_left}\\n"
        f"— img: {tr(lang,'left')} {img_left}\\n"
    )
    await q.edit_message_text(msg, reply_markup=main_menu(lang, update.effective_user.id), parse_mode=ParseMode.HTML)

async def send_ref(q, context, lang: str):
    uid = q.from_user.id
    user = db.get_user(uid)
    me = await context.bot.get_me()
    ref = referral_link(me.username, uid)
    balance = user.get("ref_balance", 0) if user else 0
    history = db.list_user_payouts(uid, limit=5)
    hist_lines = []
    for h in history:
        note = f" — {h['admin_note']}" if h.get("admin_note") else ""
        hist_lines.append(f"#{h['id']} — {h['amount']}⭐ — {h['status']}{note}")
    if not hist_lines:
        hist_lines = ["-"]
    msg = (
        f"{tr(lang,'ref_link')}:\\n{ref}\\n\\n"
        f"{tr(lang,'ref_balance')}: <b>{balance}⭐</b>\\n"
        f"{tr(lang,'ref_about')}\\n\\n"
        f"{tr(lang,'payout_hint')}\\n\\n"
        f"{tr(lang,'payout_history')}:\\n" + "\\n".join(hist_lines)
    )
    await q.edit_message_text(msg, reply_markup=main_menu(lang, update.effective_user.id), parse_mode=ParseMode.HTML)

async def send_invoice_subscription(q, context, plan_key: str, lang: str):
    p = PLANS[plan_key]
    payload = f"sub:{plan_key}:{uuid4().hex}"
    prices = [LabeledPrice(label=p["name"][lang], amount=p["price_stars"])]
    await context.bot.send_invoice(
        chat_id=q.message.chat_id,
        title="StudyAI subscription",
        description=f"{p['name'][lang]} — {p['price_stars']}⭐ / 30 days",
        payload=payload,
        provider_token="",
        currency=STARS_CURRENCY,
        prices=prices
    )

async def send_invoice_topup(q, context, topup_key: str, lang: str):
    item = TOPUPS[topup_key]
    deal = get_week_deal() if topup_key=="week_pack" else None
    if item.get("requires_sub"):
        plan, _ = db.get_limits(q.from_user.id)
        if plan=="free":
            await q.edit_message_text(tr(lang,"need_sub_for_topup"), reply_markup=sub_menu(lang, q.from_user.id)); return
    payload = f"topup:{topup_key}:{uuid4().hex}"
    prices = [LabeledPrice(label=(deal["title"][lang] if deal else item["title"][lang]), amount=(deal["stars"] if deal else item["stars"]))]
    await context.bot.send_invoice(
        chat_id=q.message.chat_id,
        title="StudyAI purchase",
        description=f"{(deal['title'][lang] if deal else item['title'][lang])} — {(deal['stars'] if deal else item['stars'])}⭐",
        payload=payload,
        provider_token="",
        currency=STARS_CURRENCY,
        prices=prices
    )

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    sp = update.message.successful_payment
    payload = sp.invoice_payload
    uid = update.effective_user.id

    db.log_payment(uid, "payment", payload, sp.total_amount)
    if not is_owner(uid):
        db.set_has_paid(uid)
        db.credit_referral_on_purchase(uid, sp.total_amount)

    try:
        kind, key, _ = payload.split(":",2)
    except Exception:
        kind, key = "unknown","unknown"

    if kind=="sub":
        until = dt.datetime.utcnow() + dt.timedelta(days=30)
        real_key = "start" if key=="start_first" else key
        db.set_plan(uid, real_key, until)
        if key=="start_first":
            try:
                db.mark_first_purchase_used(uid)
            except Exception:
                pass
        # apply promo bonus if active
        promo = db.get_active_promo(uid)
        if promo and promo.get('target_plan') == real_key:
            pk = promo.get('promo_kind')
            bonus = PROMO_BONUSES.get(pk) or {}
            if bonus:
                db.add_bonus(uid, bonus.get('add_text',0), bonus.get('add_img',0))
            db.clear_promo(uid)
    elif kind=="topup":
        if key=="week_pack":
            winner = db.get_experiment_winner("week_deal")
            var, deal = week_deal_for_user(uid or 0, winner=winner)
            try:
                db.log_offer_event(uid or 0, "impression", "week_deal", var)
            except Exception:
                pass
            db.add_bonus(uid, deal.get("add_text",0), deal.get("add_img",0))
        else:
            item = TOPUPS.get(key)
            if item:
                db.add_bonus(uid, item.get("add_text",0), item.get("add_img",0))

    await update.message.reply_text(tr(lang,"paid_ok"), reply_markup=main_menu(lang, update.effective_user.id))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_admin_text(update, context):
        return

    uid = update.effective_user.id
    if not check_rate_limit(uid, kind="text"):
        await update.message.reply_text("⏳ Слишком много запросов. Попробуй через минуту.")
        return

    # Anti-burn: repeated identical prompts in a short window
    if is_duplicate_burst(uid, update.message.text):
        await update.message.reply_text("⛔️ Похоже, ты отправляешь одно и то же слишком часто. Измени запрос и попробуй снова.")
        return

    lang = get_lang(update, context)
    text = clamp_text(update.message.text.strip())

    # Mini-games (chill): answer checking
    game = context.user_data.get("game")
    if game in ("mental", "word"):
        expected = (context.user_data.get("game_answer") or "").strip().lower()
        user_ans = text.strip().lower()
        if user_ans == expected:
            context.user_data.pop("game", None)
            context.user_data.pop("game_answer", None)
            await update.message.reply_text(
                "✅ Верно! Хочешь ещё? Открой 🎲 Отвлечься.",
                reply_markup=main_menu(lang, update.effective_user.id)
            )
            return
        await update.message.reply_text("❌ Пока нет. Попробуй ещё раз или нажми «Показать ответ».")
        return

    mode = context.user_data.get("mode", "study")
    if mode == "image":
        await handle_image(update, context, text)
    elif mode == "ege":
        await handle_ege(update, context, text)
    else:
        await handle_study(update, context, text)

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Homework photo checking via DeepSeek vision model."""
    if await handle_admin_text(update, context):
        return

    uid = update.effective_user.id
    if not check_rate_limit(uid, kind="image"):
        await update.message.reply_text("⏳ Слишком много запросов. Попробуй через минуту.")
        return

    mode = context.user_data.get("mode", "study")
    # If user is in image generation mode, guide them back to prompts.
    if mode == "image":
        lang = get_lang(update, context)
        await update.message.reply_text(tr(lang, "ask_image"), reply_markup=main_menu(lang, update.effective_user.id))
        return

    # Count as a text request (we do not sell separate "vision" limits in Stars).
    lang = get_lang(update, context)
    if not is_owner(uid):
        plan, p, text_left, *_ = db.remaining_today(uid)
        if text_left <= 0:
            await update.message.reply_text(paywall_message_limit(), reply_markup=paywall_keyboard())
            return
        db.inc_usage(uid, "text", 1)

    caption = (update.message.caption or "").strip()
    user_hint = clamp_text(caption) if caption else ""

    # Download highest-res photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    data = await file.download_as_bytearray()
    img_bytes = bytes(data)

    system = (
        "You are StudyAI, an expert tutor. "
        "This is study assistance (learning), not cheating. "
        "If the request is vague, ask up to 2 clarifying questions; otherwise proceed. "
        "Always structure the answer:\n"
        "1) краткий план/стратегия\n"
        "2) теория по теме\n"
        "3) решение/объяснение по шагам\n"
        "4) проверка и типичные ошибки\n"
        "5) мини-тренировка (2-3 похожих задания)\n"
        "Do NOT reproduce copyrighted exam texts verbatim; create original tasks. "
        "Language must match the user's language."
    )

    prompt = "Проверь домашнее задание на фото."
    if user_hint:
        prompt += f"\nПояснение пользователя: {user_hint}"

    cache_key = make_cache_key("vision", f"lang={lang}", prompt, hashlib.sha256(img_bytes).hexdigest())
    if ENABLE_TEXT_CACHE and not is_owner(uid):
        row = db.get_text_cache(cache_key, ttl_days=TEXT_CACHE_TTL_DAYS)
        if row and row.get("response"):
            await update.message.reply_text(row["response"], reply_markup=full_breakdown_keyboard())
            return

    try:
        reply = generate_vision(prompt, img_bytes, system=system)
    except Exception:
        reply = tr(lang, "error_generic")

    if ENABLE_TEXT_CACHE and not is_owner(uid) and reply and "⚠️" not in reply:
        db.set_text_cache(cache_key, reply, model="vision")

    # Store for optional full breakdown (paid users)
    context.user_data["last_prompt"] = prompt
    context.user_data["last_mode"] = "vision"
    await update.message.reply_text(reply, reply_markup=full_breakdown_keyboard())

async def handle_study(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    lang = get_lang(update, context)
    uid = update.effective_user.id
    try:
        db.inc_activity(uid, "study")
    except Exception:
        pass

    soft_paywall = False
    early_paywall = False
    plan_key = "free"
    max_tokens = MAX_TOKENS.get("free", 800)
    model = DEEPSEEK_MODEL

    if not is_owner(uid):
        plan_key, p, text_left, *_ = db.remaining_today(uid)
        if text_left <= 0:
            await update.message.reply_text(paywall_message_limit(), reply_markup=paywall_keyboard())
            return
        u = db.get_usage(uid)
        trig_winner = db.get_experiment_winner("paywall_trigger")
        _, paywall_trigger_count = paywall_trigger_count_for_user(uid, winner=trig_winner)
        # Early upsell after 2 free uses (only when trigger is 5)

        if plan_key == "free" and paywall_trigger_count >= 5 and u.get("text_used", 0) == 1:
            early_paywall = True
        # Trigger soft paywall after PAYWALL_TRIGGER_COUNT uses (e.g., 5)
        if plan_key == "free" and u.get("text_used", 0) == (paywall_trigger_count - 1):
            soft_paywall = True

        db.inc_usage(uid, "text", 1)

        max_tokens = MAX_TOKENS.get(plan_key, 900)
        model = DEEPSEEK_MODEL_FREE if plan_key == "free" else DEEPSEEK_MODEL
    else:
        max_tokens = MAX_TOKENS.get("ultra", 2200)
        model = DEEPSEEK_MODEL

    system = "You are StudyAI, a strict but friendly tutor. Do not reveal hidden chain-of-thought. Language must match the user's language."

    if plan_key == "free" and not is_owner(uid):
        # Two-level answers: concise first. Full breakdown is available via subscription.
        system += " Provide a concise helpful answer (no long essays)."
        max_tokens = min(max_tokens, 550)
    else:
        system += " Answer clearly and step-by-step."

    # Cache lookup (saves costs). Still counts towards limits.
    cache_key = make_cache_key("text", f"mode=study", f"lang={lang}", prompt)
    if ENABLE_TEXT_CACHE and not is_owner(uid):
        row = db.get_text_cache(cache_key, ttl_days=TEXT_CACHE_TTL_DAYS)
        if row and row.get("response"):
            context.user_data['last_prompt'] = prompt
            context.user_data['last_mode'] = 'study'
            await update.message.reply_text(row["response"], reply_markup=full_breakdown_keyboard())
            if early_paywall:
                await update.message.reply_text(paywall_message_early(), reply_markup=paywall_keyboard())
            if soft_paywall:
                await update.message.reply_text(paywall_message_soft(), reply_markup=paywall_keyboard())
            return

    try:
        reply = generate_text(prompt, system=system, max_tokens=max_tokens, model=model)
    except Exception:
        reply = tr(lang, "error_generic")

    if ENABLE_TEXT_CACHE and not is_owner(uid) and reply and "⚠️" not in reply:
        db.set_text_cache(cache_key, reply, model=model)

    context.user_data['last_prompt'] = prompt
    context.user_data['last_mode'] = 'study'

    await update.message.reply_text(reply, reply_markup=full_breakdown_keyboard())

    if early_paywall:
        await update.message.reply_text(paywall_message_early(), reply_markup=paywall_keyboard())

    if soft_paywall:
        await update.message.reply_text(paywall_message_soft(), reply_markup=paywall_keyboard())

    await maybe_personal_offer(update, context, plan_key)

    # personalized offers (rare)
    await maybe_personal_offer(update, context, plan_key)


async def handle_ege(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    """
    OGE/EGE preparation mode (DeepSeek).
    Avoid copyrighted past-paper text verbatim; create original tasks in same style.
    """
    lang = get_lang(update, context)
    uid = update.effective_user.id
    try:
        db.inc_activity(uid, "ege", context.user_data.get("exam"), context.user_data.get("subject"))
    except Exception:
        pass

    exam = context.user_data.get("exam")
    subject = context.user_data.get("subject")
    if subject:
        exam_str = (exam or "ege").upper()
        prompt = f"Контекст: {exam_str}, предмет: {subject_label(subject)}.\nЗапрос: {prompt}"

    soft_paywall = False
    early_paywall = False
    plan_key = "free"
    max_tokens = MAX_TOKENS.get("free", 900)
    model = DEEPSEEK_MODEL

    if not is_owner(uid):
        plan_key, p, text_left, *_ = db.remaining_today(uid)
        if text_left <= 0:
            await update.message.reply_text(paywall_message_limit(), reply_markup=paywall_keyboard())
            return
        u = db.get_usage(uid)
        trig_winner = db.get_experiment_winner("paywall_trigger")
        _, paywall_trigger_count = paywall_trigger_count_for_user(uid, winner=trig_winner)
        if plan_key == "free" and u.get("text_used", 0) == (paywall_trigger_count - 1):
            soft_paywall = True

        db.inc_usage(uid, "text", 1)
        max_tokens = MAX_TOKENS.get(plan_key, 1200)
        model = DEEPSEEK_MODEL_FREE if plan_key == "free" else DEEPSEEK_MODEL
    else:
        max_tokens = MAX_TOKENS.get("ultra", 2200)
        model = DEEPSEEK_MODEL

    system = (
        "You are StudyAI, an expert tutor. "
        "This is study assistance (learning), not cheating. "
        "If the request is vague, ask up to 2 clarifying questions; otherwise proceed. "
        "Always structure the answer:\n"
        "1) краткий план/стратегия\n"
        "2) теория по теме\n"
        "3) решение/объяснение по шагам\n"
        "4) проверка и типичные ошибки\n"
        "5) мини-тренировка (2-3 похожих задания)\n"
        "Do NOT reproduce copyrighted exam texts verbatim; create original tasks. "
        "Language must match the user's language."
    )

    cache_key = make_cache_key("text", "mode=ege", f"lang={lang}", str(exam or ""), str(subject or ""), prompt)
    if ENABLE_TEXT_CACHE and not is_owner(uid):
        row = db.get_text_cache(cache_key, ttl_days=TEXT_CACHE_TTL_DAYS)
        if row and row.get("response"):
            await update.effective_message.reply_text(row["response"])
            if early_paywall:
                await update.message.reply_text(paywall_message_early(), reply_markup=paywall_keyboard())
            if soft_paywall:
                await update.message.reply_text(paywall_message_soft(), reply_markup=paywall_keyboard())
            return

    try:
        reply = generate_text(prompt, system=system, max_tokens=max_tokens, model=model)
    except Exception:
        reply = tr(lang, "error_generic")

    if ENABLE_TEXT_CACHE and not is_owner(uid) and reply and "⚠️" not in reply:
        db.set_text_cache(cache_key, reply, model=model)

    await update.effective_message.reply_text(reply)
    if soft_paywall:
        await update.message.reply_text(paywall_message_soft(), reply_markup=paywall_keyboard())

    # personalized offers (rare)
    await maybe_personal_offer(update, context, plan_key)


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    lang = get_lang(update, context)
    uid = update.effective_user.id
    try:
        db.inc_activity(uid, "image")
    except Exception:
        pass
    if not is_owner(uid):
        plan, p, _, img_left, *_ = db.remaining_today(uid)
        if img_left<=0:
            await update.message.reply_text(tr(lang,"limit_reached_img")+"\\n\\n"+tr(lang,"upsell"), reply_markup=sub_menu(lang, q.from_user.id)); return
        db.inc_usage(uid,"img",1)

    if not STABILITY_API_KEY or not STABILITY_ENDPOINT:
        await update.message.reply_text(tr(lang,"media_not_configured")); return

    try:
        img = generate_image_bytes(prompt)
        await update.message.reply_photo(photo=img, caption="🖼")
        await maybe_personal_offer(update, context, plan_key)
    except Exception:
        await update.message.reply_text("⚠️ Ошибка генерации изображения. Попробуй позже.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    db.init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("payout", payout_cmd))
    app.add_handler(CommandHandler("payouts", payouts_cmd))
    app.add_handler(CommandHandler("revenue", revenue_cmd))
    app.add_handler(CommandHandler("skip", skip_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("StudyAI: DeepSeek text + DeepSeek vision + Stability images started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
