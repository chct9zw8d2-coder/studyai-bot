from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, date, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

DDL = """
-- Subscriptions (paid plans)
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id BIGINT PRIMARY KEY,
  plan TEXT NOT NULL,
  paid_until TIMESTAMPTZ NOT NULL,
  last_renew_reminder_day DATE
);

-- Payments / purchases
CREATE TABLE IF NOT EXISTS payments (
  telegram_charge_id TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  stars_amount INT NOT NULL,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily usage (UTC day) + same-day purchased bonuses
CREATE TABLE IF NOT EXISTS daily_usage (
  user_id BIGINT NOT NULL,
  day_utc DATE NOT NULL,
  text_used INT NOT NULL DEFAULT 0,
  img_used INT NOT NULL DEFAULT 0,
  bonus_text INT NOT NULL DEFAULT 0,
  bonus_img INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day_utc)
);
"""

MIGRATIONS = [
    # older versions may have simpler schemas; keep data and add columns
    "ALTER TABLE IF EXISTS subscriptions ADD COLUMN IF NOT EXISTS plan TEXT",
    "ALTER TABLE IF EXISTS subscriptions ADD COLUMN IF NOT EXISTS last_renew_reminder_day DATE",
    "ALTER TABLE IF EXISTS subscriptions ALTER COLUMN paid_until SET NOT NULL",
    # payments table might miss columns
    "ALTER TABLE IF EXISTS payments ADD COLUMN IF NOT EXISTS kind TEXT",
    "ALTER TABLE IF EXISTS payments ADD COLUMN IF NOT EXISTS payload TEXT",
    # daily_usage old columns
    "ALTER TABLE IF EXISTS daily_usage ADD COLUMN IF NOT EXISTS text_used INT",
    "ALTER TABLE IF EXISTS daily_usage ADD COLUMN IF NOT EXISTS img_used INT",
    "ALTER TABLE IF EXISTS daily_usage ADD COLUMN IF NOT EXISTS bonus_text INT",
    "ALTER TABLE IF EXISTS daily_usage ADD COLUMN IF NOT EXISTS bonus_img INT",
]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def today_utc() -> date:
    return utcnow().date()

@dataclass
class DB:
    dsn: str

    def _conn(self):
        return psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)

    def init(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                for stmt in MIGRATIONS:
                    try:
                        cur.execute(stmt)
                    except Exception:
                        # ignore migration failures; table may not exist yet etc.
                        pass
                # Backfill plan for old rows if plan is null
                try:
                    cur.execute("UPDATE subscriptions SET plan='Pro' WHERE plan IS NULL")
                except Exception:
                    pass
                # Backfill old daily_usage columns if they exist under old names
                # (old schema used text_count/img_count)
                try:
                    cur.execute("UPDATE daily_usage SET text_used=text_count WHERE text_used IS NULL")
                    cur.execute("UPDATE daily_usage SET img_used=img_count WHERE img_used IS NULL")
                except Exception:
                    pass
                # Ensure non-null defaults
                try:
                    cur.execute("UPDATE daily_usage SET text_used=COALESCE(text_used,0), img_used=COALESCE(img_used,0), bonus_text=COALESCE(bonus_text,0), bonus_img=COALESCE(bonus_img,0)")
                except Exception:
                    pass
            conn.commit()

    # --- subscriptions ---
    def get_subscription(self, user_id: int) -> dict | None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT plan, paid_until, last_renew_reminder_day FROM subscriptions WHERE user_id=%s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "plan": row.get("plan") or "Pro",
                    "paid_until": row["paid_until"],
                    "last_renew_reminder_day": row.get("last_renew_reminder_day"),
                }

    def set_subscription(self, user_id: int, plan: str, paid_until: datetime) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO subscriptions(user_id, plan, paid_until, last_renew_reminder_day)
                    VALUES (%s, %s, %s, NULL)
                    ON CONFLICT (user_id)
                    DO UPDATE SET plan = EXCLUDED.plan, paid_until = EXCLUDED.paid_until
                    """,
                    (user_id, plan, paid_until),
                )
            conn.commit()

    def set_last_reminder_day(self, user_id: int, day: date) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE subscriptions SET last_renew_reminder_day=%s WHERE user_id=%s",
                    (day, user_id),
                )
            conn.commit()

    def get_expiring_within(self, days: int) -> list[dict]:
        now = utcnow()
        limit = now + timedelta(days=days)
        day = today_utc()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, plan, paid_until, last_renew_reminder_day
                    FROM subscriptions
                    WHERE paid_until > %s AND paid_until <= %s
                    """,
                    (now, limit),
                )
                rows = cur.fetchall() or []
        result = []
        for r in rows:
            last_day = r.get("last_renew_reminder_day")
            if last_day == day:
                continue
            result.append(
                {
                    "user_id": int(r["user_id"]),
                    "plan": r.get("plan") or "Pro",
                    "paid_until": r["paid_until"],
                    "last_renew_reminder_day": last_day,
                }
            )
        return result

    # --- payments ---
    def record_payment(self, telegram_charge_id: str, user_id: int, stars_amount: int, kind: str, payload: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO payments(telegram_charge_id, user_id, stars_amount, kind, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (telegram_charge_id) DO NOTHING
                    """,
                    (telegram_charge_id, user_id, stars_amount, kind, payload),
                )
                inserted = cur.rowcount == 1
            conn.commit()
        return inserted

    # --- daily usage ---
    def get_daily_usage(self, user_id: int, day_utc: date | None = None) -> dict:
        if day_utc is None:
            day_utc = today_utc()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT text_used, img_used, bonus_text, bonus_img FROM daily_usage WHERE user_id=%s AND day_utc=%s",
                    (user_id, day_utc),
                )
                row = cur.fetchone()
                if not row:
                    return {"text_used": 0, "img_used": 0, "bonus_text": 0, "bonus_img": 0}
                return {
                    "text_used": int(row.get("text_used") or 0),
                    "img_used": int(row.get("img_used") or 0),
                    "bonus_text": int(row.get("bonus_text") or 0),
                    "bonus_img": int(row.get("bonus_img") or 0),
                }

    def _ensure_row(self, user_id: int, day_utc: date) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_usage(user_id, day_utc, text_used, img_used, bonus_text, bonus_img)
                    VALUES (%s, %s, 0, 0, 0, 0)
                    ON CONFLICT (user_id, day_utc) DO NOTHING
                    """,
                    (user_id, day_utc),
                )
            conn.commit()

    def inc_text(self, user_id: int, day_utc: date | None = None) -> None:
        if day_utc is None:
            day_utc = today_utc()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_usage(user_id, day_utc, text_used, img_used, bonus_text, bonus_img)
                    VALUES (%s, %s, 1, 0, 0, 0)
                    ON CONFLICT (user_id, day_utc)
                    DO UPDATE SET text_used = daily_usage.text_used + 1
                    """,
                    (user_id, day_utc),
                )
            conn.commit()

    def inc_img(self, user_id: int, day_utc: date | None = None) -> None:
        if day_utc is None:
            day_utc = today_utc()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_usage(user_id, day_utc, text_used, img_used, bonus_text, bonus_img)
                    VALUES (%s, %s, 0, 1, 0, 0)
                    ON CONFLICT (user_id, day_utc)
                    DO UPDATE SET img_used = daily_usage.img_used + 1
                    """,
                    (user_id, day_utc),
                )
            conn.commit()

    def add_bonus(self, user_id: int, bonus_text: int, bonus_img: int, day_utc: date | None = None) -> None:
        if day_utc is None:
            day_utc = today_utc()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_usage(user_id, day_utc, text_used, img_used, bonus_text, bonus_img)
                    VALUES (%s, %s, 0, 0, %s, %s)
                    ON CONFLICT (user_id, day_utc)
                    DO UPDATE SET bonus_text = daily_usage.bonus_text + EXCLUDED.bonus_text,
                                  bonus_img = daily_usage.bonus_img + EXCLUDED.bonus_img
                    """,
                    (user_id, day_utc, bonus_text, bonus_img),
                )
            conn.commit()

def is_active(paid_until) -> bool:
    if not paid_until:
        return False
    return paid_until > utcnow()
