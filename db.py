import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, date

from config import DATABASE_URL, PLANS, SUB_DAYS

def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is empty. Add it in Railway Variables.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            plan TEXT NOT NULL DEFAULT 'free',
            expires_at TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS usage_daily (
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            day DATE NOT NULL,
            text_used INT NOT NULL DEFAULT 0,
            img_used INT NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, day)
        );

        CREATE TABLE IF NOT EXISTS topups (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            amount INT NOT NULL,
            remaining INT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        conn.commit()

def upsert_user(user_id: int):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO users(user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
        cur.execute("INSERT INTO subscriptions(user_id, plan) VALUES (%s,'free') ON CONFLICT DO NOTHING", (user_id,))
        conn.commit()

def get_subscription(user_id: int):
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT plan, expires_at FROM subscriptions WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            return {"plan":"free","expires_at":None,"active":False}
        plan = row["plan"] or "free"
        exp = row["expires_at"]
        active = False
        if plan != "free" and exp is not None and exp > datetime.utcnow():
            active = True
        return {"plan": plan, "expires_at": exp, "active": active}

def set_subscription(user_id: int, plan: str):
    if plan not in PLANS:
        plan = "free"
    expires = datetime.utcnow() + timedelta(days=SUB_DAYS) if plan != "free" else None
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE subscriptions SET plan=%s, expires_at=%s, updated_at=NOW() WHERE user_id=%s",
            (plan, expires, user_id)
        )
        conn.commit()

def _ensure_usage_row(cur, user_id: int, day: date):
    cur.execute(
        "INSERT INTO usage_daily(user_id, day) VALUES (%s,%s) ON CONFLICT DO NOTHING",
        (user_id, day)
    )

def get_limits(user_id: int):
    sub = get_subscription(user_id)
    plan_key = sub["plan"] if sub["active"] else "free"
    plan = PLANS.get(plan_key, PLANS["free"])
    return plan_key, plan

def get_usage(user_id: int, day: date):
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT text_used, img_used FROM usage_daily WHERE user_id=%s AND day=%s", (user_id, day))
        row = cur.fetchone()
        if not row:
            return {"text_used":0,"img_used":0}
        return row

def add_usage(user_id: int, day: date, kind: str, amount: int = 1):
    with _connect() as conn, conn.cursor() as cur:
        _ensure_usage_row(cur, user_id, day)
        if kind == "text":
            cur.execute("UPDATE usage_daily SET text_used = text_used + %s WHERE user_id=%s AND day=%s", (amount, user_id, day))
        elif kind == "img":
            cur.execute("UPDATE usage_daily SET img_used = img_used + %s WHERE user_id=%s AND day=%s", (amount, user_id, day))
        conn.commit()

def add_topup(user_id: int, kind: str, amount: int):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO topups(user_id, kind, amount, remaining) VALUES (%s,%s,%s,%s)", (user_id, kind, amount, amount))
        conn.commit()

def consume_topup(user_id: int, kind: str, amount: int = 1) -> bool:
    """Try to consume from oldest topup. Return True if consumed."""
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, remaining FROM topups WHERE user_id=%s AND kind=%s AND remaining>0 ORDER BY id ASC LIMIT 1",
            (user_id, kind)
        )
        row = cur.fetchone()
        if not row:
            return False
        if row["remaining"] < amount:
            return False
        cur2 = conn.cursor()
        cur2.execute("UPDATE topups SET remaining = remaining - %s WHERE id=%s", (amount, row["id"]))
        conn.commit()
        return True
