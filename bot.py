import datetime as dt
from uuid import uuid4

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, ContextTypes, filters

import db
from config import TELEGRAM_BOT_TOKEN, PLANS, TOPUPS, STARS_CURRENCY
from i18n import detect_lang, tr
from ai.deepseek import generate_text
from ai.pollinations import generate_image_bytes
from ai.music_free import generate_wav

def main_menu(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang,'menu_study'), callback_data='mode:study')],
        [InlineKeyboardButton(tr(lang,'menu_image'), callback_data='mode:image')],
        [InlineKeyboardButton(tr(lang,'menu_chill'), callback_data='menu:chill')],
        [InlineKeyboardButton(tr(lang,'menu_sub'), callback_data='menu:sub')],
        [InlineKeyboardButton(tr(lang,'menu_topup'), callback_data='menu:topup')],
        [InlineKeyboardButton(tr(lang,'menu_profile'), callback_data='menu:profile')],
        [InlineKeyboardButton(tr(lang,'menu_help'), callback_data='menu:help')],
    ])

def chill_menu(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(lang,'chill_song'), callback_data='chill:song')],
        [InlineKeyboardButton(tr(lang,'chill_fact'), callback_data='chill:fact')],
        [InlineKeyboardButton(tr(lang,'back'), callback_data='menu:main')],
    ])

def sub_menu(lang: str):
    btn=[]
    for k in ('pro','ultra'):
        p=PLANS[k]
        btn.append([InlineKeyboardButton(f"{p['name'][lang]} — {p['price_stars']}⭐", callback_data=f"buy:sub:{k}")])
    btn.append([InlineKeyboardButton(tr(lang,'back'), callback_data='menu:main')])
    return InlineKeyboardMarkup(btn)

def topup_menu(lang: str):
    btn=[]
    for k,it in TOPUPS.items():
        btn.append([InlineKeyboardButton(f"{it['title'][lang]} — {it['price_stars']}⭐", callback_data=f"buy:topup:{k}")])
    btn.append([InlineKeyboardButton(tr(lang,'back'), callback_data='menu:main')])
    return InlineKeyboardMarkup(btn)

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if 'lang' in context.user_data:
        return context.user_data['lang']
    lang = detect_lang(getattr(update.effective_user,'language_code',None), getattr(update.effective_message,'text',None))
    context.user_data['lang']=lang
    return lang

def referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref{user_id}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    inviter=None
    if context.args and context.args[0].startswith('ref'):
        try:
            inviter=int(context.args[0].replace('ref',''))
            if inviter==update.effective_user.id:
                inviter=None
        except Exception:
            inviter=None
    db.upsert_user(update.effective_user.id, lang=lang, inviter_id=inviter)
    await update.message.reply_text(
        f"<b>{tr(lang,'welcome_title')}</b>\n\n{tr(lang,'welcome_body')}",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(lang)
    )

async def text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang=get_lang(update, context)
    if not context.args:
        await update.message.reply_text(tr(lang,'hint_text_cmd'))
        return
    context.user_data['mode']='study'
    await handle_study(update, context, ' '.join(context.args))

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    lang=get_lang(update, context)
    d=q.data

    if d=='menu:main':
        await q.edit_message_text(tr(lang,'welcome_body'), reply_markup=main_menu(lang))
        return
    if d.startswith('mode:'):
        mode=d.split(':',1)[1]
        context.user_data['mode']=mode
        if mode=='study':
            await q.edit_message_text(tr(lang,'ask_study'), reply_markup=main_menu(lang))
        elif mode=='image':
            await q.edit_message_text(tr(lang,'ask_image'), reply_markup=main_menu(lang))
        else:
            await q.edit_message_text(tr(lang,'ask_study'), reply_markup=main_menu(lang))
        return
    if d=='menu:chill':
        await q.edit_message_text(tr(lang,'chill_menu'), reply_markup=chill_menu(lang))
        return
    if d=='menu:sub':
        await q.edit_message_text('⭐', reply_markup=sub_menu(lang))
        return
    if d=='menu:topup':
        await q.edit_message_text('🛒', reply_markup=topup_menu(lang))
        return
    if d=='menu:help':
        await q.edit_message_text(tr(lang,'help'), reply_markup=main_menu(lang))
        return
    if d=='menu:profile':
        await send_profile(q, context, lang)
        return
    if d=='chill:fact':
        fact=generate_text('Give one short surprising fact (1 sentence).', system='You are a fun fact generator.')
        await q.edit_message_text('😄 '+fact, reply_markup=chill_menu(lang))
        return
    if d=='chill:song':
        plan, p, text_left, img_left, song_left, u = db.remaining_today(q.from_user.id)
        if song_left<=0:
            await q.edit_message_text(tr(lang,'limit_reached_song')+'\n\n'+tr(lang,'upsell'), reply_markup=topup_menu(lang))
            return
        db.inc_usage(q.from_user.id,'song',1)
        db.maybe_reward_referral(q.from_user.id)
        wav=generate_wav(seconds=30, genre='lofi')
        await context.bot.send_audio(chat_id=q.message.chat_id, audio=wav, filename='studyai_track.wav', title='StudyAI Track')
        await q.edit_message_text('🎧', reply_markup=chill_menu(lang))
        return
    if d.startswith('buy:sub:'):
        await send_invoice_subscription(q, context, d.split(':')[2], lang); return
    if d.startswith('buy:topup:'):
        await send_invoice_topup(q, context, d.split(':')[2], lang); return

async def send_profile(q, context, lang):
    uid=q.from_user.id
    user=db.get_user(uid)
    plan, p, text_left, img_left, song_left, u = db.remaining_today(uid)
    me=await context.bot.get_me()
    ref=referral_link(me.username, uid)
    sub_until=user.get('sub_until')
    sub_str=sub_until.strftime('%Y-%m-%d') if sub_until else '-'
    msg=(f"<b>{tr(lang,'profile')}</b>\n"
         f"{tr(lang,'plan')}: <b>{plan.upper()}</b>\n"
         f"{tr(lang,'until')}: {sub_str}\n\n"
         f"{tr(lang,'today')}:\n"
         f"— text: {tr(lang,'left')} {text_left}\n"
         f"— img: {tr(lang,'left')} {img_left}\n"
         f"— song: {tr(lang,'left')} {song_left}\n\n"
         f"{tr(lang,'ref_link')}:\n{ref}\n"
         f"<i>{tr(lang,'ref_about')}</i>")
    await q.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=main_menu(lang))

async def send_invoice_subscription(q, context, plan_key, lang):
    p=PLANS[plan_key]
    payload=f"sub:{plan_key}:{uuid4().hex}"
    prices=[LabeledPrice(label=p['name'][lang], amount=p['price_stars'])]
    await context.bot.send_invoice(chat_id=q.message.chat_id, title=tr(lang,'payment_title_sub'),
        description=f"{p['name'][lang]} — {p['price_stars']}⭐ / 30 days",
        payload=payload, provider_token='', currency=STARS_CURRENCY, prices=prices)

async def send_invoice_topup(q, context, topup_key, lang):
    it=TOPUPS[topup_key]
    if it.get('requires_sub'):
        plan,_=db.get_limits(q.from_user.id)
        if plan=='free':
            await q.edit_message_text(tr(lang,'need_sub_for_topup'), reply_markup=sub_menu(lang))
            return
    payload=f"topup:{topup_key}:{uuid4().hex}"
    prices=[LabeledPrice(label=it['title'][lang], amount=it['price_stars'])]
    await context.bot.send_invoice(chat_id=q.message.chat_id, title=tr(lang,'payment_title_topup'),
        description=f"{it['title'][lang]} — {it['price_stars']}⭐",
        payload=payload, provider_token='', currency=STARS_CURRENCY, prices=prices)

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang=get_lang(update, context)
    sp=update.message.successful_payment
    payload=sp.invoice_payload
    uid=update.effective_user.id
    parts=payload.split(':',2)
    kind=parts[0] if len(parts)>0 else 'unknown'
    key=parts[1] if len(parts)>1 else 'unknown'
    if kind=='sub':
        until=dt.datetime.utcnow()+dt.timedelta(days=30)
        db.set_plan(uid, key, until)
        db.log_payment(uid,'sub',payload,sp.total_amount)
    elif kind=='topup':
        it=TOPUPS.get(key)
        if it:
            db.add_bonus(uid, it.get('add_text',0), it.get('add_img',0), it.get('add_song',0))
            db.log_payment(uid,'topup',payload,sp.total_amount)
    await update.message.reply_text(tr(lang,'paid_ok'), reply_markup=main_menu(lang))

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang=get_lang(update, context)
    text=update.message.text.strip()
    mode=context.user_data.get('mode','study')
    if mode=='image':
        await handle_image(update, context, text)
    else:
        await handle_study(update, context, text)

async def handle_study(update, context, prompt):
    lang=get_lang(update, context)
    uid=update.effective_user.id
    plan,p,text_left,img_left,song_left,u=db.remaining_today(uid)
    if text_left<=0:
        await update.message.reply_text(tr(lang,'limit_reached_text')+'\n\n'+tr(lang,'upsell'), reply_markup=sub_menu(lang))
        return
    system=("You are StudyAI, a strict but friendly tutor. Answer clearly and step-by-step. "
            "Do not reveal hidden chain-of-thought. Language must match the user's language.")
    try:
        reply=generate_text(prompt, system=system, max_tokens=900)
    except Exception:
        reply=tr(lang,'error_generic')
    db.inc_usage(uid,'text',1)
    db.maybe_reward_referral(uid)
    await update.message.reply_text(reply)

async def handle_image(update, context, prompt):
    lang=get_lang(update, context)
    uid=update.effective_user.id
    plan,p,text_left,img_left,song_left,u=db.remaining_today(uid)
    if img_left<=0:
        await update.message.reply_text(tr(lang,'limit_reached_img')+'\n\n'+tr(lang,'upsell'), reply_markup=sub_menu(lang))
        return
    try:
        img=generate_image_bytes(prompt)
        db.inc_usage(uid,'img',1)
        db.maybe_reward_referral(uid)
        await update.message.reply_photo(photo=img, caption='🖼')
    except Exception:
        await update.message.reply_text('⚠️ Image service is busy. Try again in a minute.')

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not set')
    db.init_db()
    app=Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('text', text_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print('StudyAI v2 started')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=='__main__':
    main()
