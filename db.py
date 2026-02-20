import datetime as dt
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL, PLANS, REF_BONUS_INVITER, REF_BONUS_INVITEE

def _conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id BIGINT PRIMARY KEY,
                lang TEXT DEFAULT 'en',
                plan TEXT DEFAULT 'free',
                sub_until TIMESTAMP NULL,
                inviter_id BIGINT NULL,
                referral_rewarded BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")
            cur.execute("""CREATE TABLE IF NOT EXISTS daily_usage(
                user_id BIGINT NOT NULL,
                day DATE NOT NULL,
                text_used INT DEFAULT 0,
                img_used INT DEFAULT 0,
                song_used INT DEFAULT 0,
                text_bonus INT DEFAULT 0,
                img_bonus INT DEFAULT 0,
                song_bonus INT DEFAULT 0,
                PRIMARY KEY(user_id, day)
            );""")
            cur.execute("""CREATE TABLE IF NOT EXISTS payments(
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                stars INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")
        conn.commit()

def upsert_user(user_id: int, lang: str, inviter_id: int|None=None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
            if cur.fetchone() is None:
                cur.execute("INSERT INTO users(user_id, lang, inviter_id) VALUES(%s,%s,%s)", (user_id, lang, inviter_id))
            else:
                cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, user_id))
        conn.commit()

def get_user(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            return cur.fetchone()

def set_plan(user_id: int, plan: str, sub_until: dt.datetime|None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET plan=%s, sub_until=%s WHERE user_id=%s", (plan, sub_until, user_id))
        conn.commit()

def _today(): return dt.date.today()

def get_usage(user_id: int):
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM daily_usage WHERE user_id=%s AND day=%s", (user_id, day))
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO daily_usage(user_id, day) VALUES(%s,%s)", (user_id, day))
                conn.commit()
                cur.execute("SELECT * FROM daily_usage WHERE user_id=%s AND day=%s", (user_id, day))
                row = cur.fetchone()
            return row

def add_bonus(user_id: int, add_text=0, add_img=0, add_song=0):
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO daily_usage(user_id, day, text_bonus, img_bonus, song_bonus)
                VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(user_id, day) DO UPDATE SET
                  text_bonus = daily_usage.text_bonus + EXCLUDED.text_bonus,
                  img_bonus  = daily_usage.img_bonus  + EXCLUDED.img_bonus,
                  song_bonus = daily_usage.song_bonus + EXCLUDED.song_bonus
            """, (user_id, day, add_text, add_img, add_song))
        conn.commit()

def inc_usage(user_id: int, kind: str, amount: int=1):
    init_db()
    day = _today()
    col = {"text":"text_used","img":"img_used","song":"song_used"}[kind]
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""INSERT INTO daily_usage(user_id, day, {col})
                VALUES(%s,%s,%s)
                ON CONFLICT(user_id, day) DO UPDATE SET {col} = daily_usage.{col} + EXCLUDED.{col}
            """, (user_id, day, amount))
        conn.commit()

def get_limits(user_id: int):
    user = get_user(user_id)
    plan = user["plan"] if user else "free"
    sub_until = user.get("sub_until") if user else None
    if plan != "free" and sub_until and dt.datetime.utcnow() > sub_until.replace(tzinfo=None):
        plan = "free"
    return plan, PLANS.get(plan, PLANS["free"])

def remaining_today(user_id: int):
    plan, p = get_limits(user_id)
    u = get_usage(user_id)
    text_left = max(0, p["daily_text"] + u["text_bonus"] - u["text_used"])
    img_left  = max(0, p["daily_img"]  + u["img_bonus"]  - u["img_used"])
    song_left = max(0, p["daily_song"] + u["song_bonus"] - u["song_used"])
    return plan, p, text_left, img_left, song_left, u

def maybe_reward_referral(user_id: int):
    user = get_user(user_id)
    if not user or user["referral_rewarded"] or not user["inviter_id"]:
        return False
    inviter_id = user["inviter_id"]
    add_bonus(inviter_id, **REF_BONUS_INVITER)
    add_bonus(user_id, **REF_BONUS_INVITEE)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET referral_rewarded=TRUE WHERE user_id=%s", (user_id,))
        conn.commit()
    return True

def log_payment(user_id: int, kind: str, payload: str, stars: int):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payments(user_id, kind, payload, stars) VALUES(%s,%s,%s,%s)", (user_id, kind, payload, stars))
        conn.commit()
