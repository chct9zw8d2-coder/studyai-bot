
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, date, timedelta, timezone

DATABASE_URL = os.getenv("DATABASE_URL")

def _conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                state TEXT,
                state_payload JSONB
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                plan TEXT NOT NULL,
                paid_until TIMESTAMPTZ NOT NULL
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                day DATE NOT NULL,
                text_used INT NOT NULL DEFAULT 0,
                img_used INT NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, day)
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_topups (
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                day DATE NOT NULL,
                text_bonus INT NOT NULL DEFAULT 0,
                img_bonus INT NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, day)
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                payload JSONB,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """)
            conn.commit()

def upsert_user(user_id: int):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO users (user_id) VALUES (%s)
            ON CONFLICT (user_id) DO UPDATE SET last_seen=NOW()
            """, (user_id,))
            conn.commit()

def set_state(user_id: int, state: str | None, payload: dict | None = None):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            UPDATE users SET state=%s, state_payload=%s, last_seen=NOW() WHERE user_id=%s
            """, (state, psycopg2.extras.Json(payload) if payload else None, user_id))
            conn.commit()

def get_state(user_id: int):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT state, state_payload FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            if not row:
                return None, None
            return row["state"], row["state_payload"]

def get_subscription(user_id: int):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT plan, paid_until FROM subscriptions WHERE user_id=%s", (user_id,))
            return cur.fetchone()

def set_subscription(user_id: int, plan: str, paid_until):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO subscriptions (user_id, plan, paid_until)
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET plan=EXCLUDED.plan, paid_until=EXCLUDED.paid_until
            """, (user_id, plan, paid_until))
            conn.commit()

def add_subscription_days(user_id: int, plan: str, days: int):
    sub = get_subscription(user_id)
    now = datetime.now(timezone.utc)
    if sub and sub["paid_until"] and sub["paid_until"] > now:
        new_until = sub["paid_until"] + timedelta(days=days)
    else:
        new_until = now + timedelta(days=days)
    set_subscription(user_id, plan, new_until)
    return new_until

def _today_utc() -> date:
    return datetime.now(timezone.utc).date()

def get_daily_usage(user_id: int, day: date | None = None):
    day = day or _today_utc()
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT text_used, img_used FROM daily_usage WHERE user_id=%s AND day=%s", (user_id, day))
            row = cur.fetchone()
            if not row:
                return {"text_used": 0, "img_used": 0}
            return row

def inc_daily_usage(user_id: int, text_inc: int = 0, img_inc: int = 0, day: date | None = None):
    day = day or _today_utc()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO daily_usage (user_id, day, text_used, img_used)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (user_id, day) DO UPDATE
            SET text_used = daily_usage.text_used + EXCLUDED.text_used,
                img_used = daily_usage.img_used + EXCLUDED.img_used
            """, (user_id, day, text_inc, img_inc))
            conn.commit()

def get_daily_topup(user_id: int, day: date | None = None):
    day = day or _today_utc()
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT text_bonus, img_bonus FROM daily_topups WHERE user_id=%s AND day=%s", (user_id, day))
            row = cur.fetchone()
            if not row:
                return {"text_bonus": 0, "img_bonus": 0}
            return row

def add_daily_topup(user_id: int, text_bonus: int, img_bonus: int, day: date | None = None):
    day = day or _today_utc()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO daily_topups (user_id, day, text_bonus, img_bonus)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (user_id, day) DO UPDATE
            SET text_bonus = daily_topups.text_bonus + EXCLUDED.text_bonus,
                img_bonus = daily_topups.img_bonus + EXCLUDED.img_bonus
            """, (user_id, day, text_bonus, img_bonus))
            conn.commit()

def create_order(order_id: str, user_id: int, kind: str, payload: dict):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO orders (order_id, user_id, kind, payload) VALUES (%s,%s,%s,%s)
            ON CONFLICT (order_id) DO NOTHING
            """, (order_id, user_id, kind, psycopg2.extras.Json(payload)))
            conn.commit()

def mark_order_paid(order_id: str):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status='paid' WHERE order_id=%s", (order_id,))
            conn.commit()

def get_order(order_id: str):
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
            return cur.fetchone()
