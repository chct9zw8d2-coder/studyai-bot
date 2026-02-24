import json
import datetime as dt
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL, PLANS, REF_PERCENT, MIN_PAYOUT_STARS, PAYOUT_COOLDOWN_HOURS, REF_REQUIRE_FIRST_PAYMENT

def _conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
              user_id BIGINT PRIMARY KEY,
              lang TEXT DEFAULT 'en',
              plan TEXT DEFAULT 'free',
              sub_until TIMESTAMP NULL,
              inviter_id BIGINT NULL,
              ref_balance INT DEFAULT 0,
              payout_last_ts TIMESTAMP NULL,
              has_paid BOOLEAN DEFAULT FALSE,
              trial_used BOOLEAN DEFAULT FALSE,
              first_purchase_used BOOLEAN DEFAULT FALSE,
              grade_photo_trial_used BOOLEAN DEFAULT FALSE,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            # One-time free photo grading (marketing trigger)
            try:
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS grade_photo_trial_used BOOLEAN DEFAULT FALSE;")
            except Exception:
                pass


            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
              user_id BIGINT NOT NULL,
              day DATE NOT NULL,
              text_used INT DEFAULT 0,
              img_used INT DEFAULT 0,
              text_bonus INT DEFAULT 0,
              img_bonus INT DEFAULT 0,
              PRIMARY KEY (user_id, day)
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
              id SERIAL PRIMARY KEY,
              user_id BIGINT NOT NULL,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              stars INT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
              id SERIAL PRIMARY KEY,
              user_id BIGINT NOT NULL,
              kind TEXT NOT NULL,
              subject TEXT NULL,
              prompt TEXT NOT NULL,
              response TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")
            # Migration: add subject column if upgrading
            cur.execute("ALTER TABLE user_history ADD COLUMN IF NOT EXISTS subject TEXT NULL;")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS payout_requests (
              id SERIAL PRIMARY KEY,
              user_id BIGINT NOT NULL,
              amount INT NOT NULL,
              status TEXT NOT NULL DEFAULT 'new',
              admin_note TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_counts (
              user_id BIGINT NOT NULL,
              day DATE NOT NULL,
              mode TEXT NOT NULL,
              exam TEXT NULL,
              subject TEXT NULL,
              cnt INT DEFAULT 0,
              PRIMARY KEY (user_id, day, mode, exam, subject)
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS ab_assignments (
              user_id BIGINT NOT NULL,
              experiment TEXT NOT NULL,
              variant TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT NOW(),
              PRIMARY KEY (user_id, experiment)
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS offer_events (
              id BIGSERIAL PRIMARY KEY,
              user_id BIGINT NOT NULL,
              ts TIMESTAMP DEFAULT NOW(),
              event TEXT NOT NULL,
              offer_key TEXT NOT NULL,
              variant TEXT NULL,
              meta JSONB NULL
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS promos (
              user_id BIGINT PRIMARY KEY,
              promo_kind TEXT NOT NULL,
              target_plan TEXT NOT NULL,
              expires_at TIMESTAMP NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS text_cache (
              key TEXT PRIMARY KEY,
              response TEXT NOT NULL,
              model TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              hits INT DEFAULT 0
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS image_cache (
              key TEXT PRIMARY KEY,
              telegram_file_id TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              hits INT DEFAULT 0
            );""")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS experiment_winners (
              experiment TEXT PRIMARY KEY,
              winner TEXT NOT NULL,
              updated_at TIMESTAMP DEFAULT NOW()
            );""")

        conn.commit()

def upsert_user(user_id: int, lang: str, inviter_id: int | None = None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT inviter_id FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO users (user_id, lang, inviter_id) VALUES (%s,%s,%s)", (user_id, lang, inviter_id))
            else:
                cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, user_id))
        conn.commit()

def get_user(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            return cur.fetchone()


def is_grade_photo_trial_used(user_id: int) -> bool:
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT grade_photo_trial_used FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            if not row:
                return False
            return bool(row[0])

def set_grade_photo_trial_used(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET grade_photo_trial_used=TRUE WHERE user_id=%s", (user_id,))
        conn.commit()

def set_has_paid(user_id: int):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET has_paid=TRUE WHERE user_id=%s", (user_id,))
        conn.commit()

def set_plan(user_id: int, plan: str, sub_until: dt.datetime | None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET plan=%s, sub_until=%s WHERE user_id=%s", (plan, sub_until, user_id))
        conn.commit()

def _today():
    return dt.date.today()

def get_usage(user_id: int):
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM daily_usage WHERE user_id=%s AND day=%s", (user_id, day))
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO daily_usage (user_id, day) VALUES (%s,%s)", (user_id, day))
                conn.commit()
                cur.execute("SELECT * FROM daily_usage WHERE user_id=%s AND day=%s", (user_id, day))
                row = cur.fetchone()
            return row

def add_bonus(user_id: int, add_text=0, add_img=0, add_song=0):
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO daily_usage (user_id, day, text_bonus, img_bonus, song_bonus)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (user_id, day)
            DO UPDATE SET
              text_bonus = daily_usage.text_bonus + EXCLUDED.text_bonus,
              img_bonus  = daily_usage.img_bonus  + EXCLUDED.img_bonus,
              song_bonus = daily_usage.song_bonus + EXCLUDED.song_bonus
            """, (user_id, day, add_text, add_img, add_song))
        conn.commit()

def inc_usage(user_id: int, kind: str, amount: int = 1):
    init_db()
    day = _today()
    col = {"text":"text_used","img":"img_used","song":"song_used"}[kind]
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
            INSERT INTO daily_usage (user_id, day, {col})
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id, day)
            DO UPDATE SET {col} = daily_usage.{col} + EXCLUDED.{col}
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
    # Music feature was removed. Keep DB columns for backward compatibility.
    song_left = max(0, p.get("daily_song", 0) + u["song_bonus"] - u["song_used"])
    return plan, p, text_left, img_left, song_left, u

def log_payment(user_id: int, kind: str, payload: str, stars: int):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payments (user_id, kind, payload, stars) VALUES (%s,%s,%s,%s)",
                        (user_id, kind, payload, stars))
        conn.commit()

def credit_referral_on_purchase(buyer_id: int, stars_paid: int) -> int:
    user = get_user(buyer_id)
    if not user or not user.get("inviter_id"):
        return 0
    if REF_REQUIRE_FIRST_PAYMENT and not user.get("has_paid"):
        return 0
    inviter = int(user["inviter_id"])
    bonus = int(round(stars_paid * REF_PERCENT))
    if bonus <= 0:
        return 0
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET ref_balance = ref_balance + %s WHERE user_id=%s", (bonus, inviter))
        conn.commit()
    return bonus

def can_request_payout(user_id: int):
    user = get_user(user_id)
    if not user:
        return False, "no_user"
    if user["ref_balance"] < MIN_PAYOUT_STARS:
        return False, "too_small"
    last = user.get("payout_last_ts")
    if last:
        delta = dt.datetime.utcnow() - last.replace(tzinfo=None)
        if delta.total_seconds() < PAYOUT_COOLDOWN_HOURS * 3600:
            return False, "cooldown"
    return True, "ok"

def create_payout_request(user_id: int, amount: int) -> int:
    init_db()
    user = get_user(user_id)
    if amount < MIN_PAYOUT_STARS:
        raise ValueError("too_small")
    if user["ref_balance"] < amount:
        raise ValueError("not_enough")
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payout_requests (user_id, amount) VALUES (%s,%s) RETURNING id", (user_id, amount))
            pid = cur.fetchone()[0]
            cur.execute("UPDATE users SET payout_last_ts=NOW() WHERE user_id=%s", (user_id,))
        conn.commit()
    return pid

def list_user_payouts(user_id: int, limit: int = 10):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT id, amount, status, created_at, admin_note
            FROM payout_requests
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT %s
            """, (user_id, limit))
            return cur.fetchall()

def list_new_payouts(limit: int = 10):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT id, user_id, amount, created_at
            FROM payout_requests
            WHERE status='new'
            ORDER BY created_at ASC
            LIMIT %s
            """, (limit,))
            return cur.fetchall()

def get_payout(pid: int):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM payout_requests WHERE id=%s", (pid,))
            return cur.fetchone()

def approve_payout(pid: int) -> bool:
    req = get_payout(pid)
    if not req or req["status"] != "new":
        return False
    user_id = int(req["user_id"]); amount = int(req["amount"])
    user = get_user(user_id)
    if not user or user["ref_balance"] < amount:
        reject_payout(pid, "Insufficient balance at approval")
        return False
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET ref_balance = ref_balance - %s WHERE user_id=%s", (amount, user_id))
            cur.execute("UPDATE payout_requests SET status='paid', updated_at=NOW() WHERE id=%s", (pid,))
        conn.commit()
    return True

def reject_payout(pid: int, note: str = "Rejected by admin") -> bool:
    req = get_payout(pid)
    if not req or req["status"] != "new":
        return False
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE payout_requests SET status='rejected', admin_note=%s, updated_at=NOW() WHERE id=%s", (note, pid))
        conn.commit()
    return True

def revenue_summary(days: int = 7):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COALESCE(SUM(stars),0) AS total FROM payments WHERE created_at >= NOW() - (%s || ' days')::interval", (days,))
            total = int(cur.fetchone()["total"] or 0)
            cur.execute("""
              SELECT DATE(created_at) AS day, COALESCE(SUM(stars),0) AS stars
              FROM payments
              WHERE created_at >= NOW() - (%s || ' days')::interval
              GROUP BY 1
              ORDER BY 1 DESC
            """, (days,))
            by_day = cur.fetchall()
            cur.execute("""
              SELECT kind, COALESCE(SUM(stars),0) AS stars
              FROM payments
              WHERE created_at >= NOW() - (%s || ' days')::interval
              GROUP BY 1
              ORDER BY stars DESC
            """, (days,))
            by_kind = cur.fetchall()
    return total, by_day, by_kind


def admin_summary():
    """Lightweight admin dashboard numbers."""
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM daily_usage WHERE day=%s", (day,))
            active_today = cur.fetchone()[0]
            cur.execute(
                "SELECT COALESCE(SUM(text_used),0), COALESCE(SUM(img_used),0) FROM daily_usage WHERE day=%s",
                (day,),
            )
            text_used, img_used = cur.fetchone()
    return {
        "total_users": int(total_users),
        "active_today": int(active_today),
        "text_used": int(text_used),
        "img_used": int(img_used),
    }


# ----------------
# Caching helpers
# ----------------

def get_text_cache(key: str, *, ttl_days: int | None = None):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if ttl_days:
                cur.execute(
                    "SELECT response, model, created_at FROM text_cache WHERE key=%s AND created_at >= (CURRENT_TIMESTAMP - INTERVAL '%s days')",
                    (key, int(ttl_days)),
                )
            else:
                cur.execute("SELECT response, model, created_at FROM text_cache WHERE key=%s", (key,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE text_cache SET hits = hits + 1, last_hit = CURRENT_TIMESTAMP WHERE key=%s", (key,))
                conn.commit()
            return row

def set_text_cache(key: str, response: str, model: str | None = None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO text_cache (key, response, model)
                VALUES (%s,%s,%s)
                ON CONFLICT (key) DO UPDATE SET
                  response = EXCLUDED.response,
                  model = EXCLUDED.model,
                  created_at = CURRENT_TIMESTAMP,
                  last_hit = CURRENT_TIMESTAMP
                """,
                (key, response, model),
            )
        conn.commit()



def set_promo(user_id: int, promo_kind: str, target_plan: str, expires_at: dt.datetime):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO promos (user_id, promo_kind, target_plan, expires_at)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET promo_kind=EXCLUDED.promo_kind, target_plan=EXCLUDED.target_plan, expires_at=EXCLUDED.expires_at
            """, (user_id, promo_kind, target_plan, expires_at))
        conn.commit()

def get_active_promo(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT * FROM promos WHERE user_id=%s AND expires_at > CURRENT_TIMESTAMP""", (user_id,))
            return cur.fetchone()

def clear_promo(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM promos WHERE user_id=%s", (user_id,))
        conn.commit()



def inc_activity(user_id: int, mode: str, exam: str | None = None, subject: str | None = None, amount: int = 1):
    """Increment activity counter used for behavior-based offers."""
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO activity_counts (user_id, day, mode, exam, subject, cnt)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id, day, mode, exam, subject)
            DO UPDATE SET cnt = activity_counts.cnt + EXCLUDED.cnt
            """, (user_id, day, mode, exam, subject, amount))
        conn.commit()

def get_top_focus(user_id: int):
    """Return (mode, exam, subject, cnt) for today's most used focus."""
    init_db()
    day = _today()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT mode, exam, subject, cnt
            FROM activity_counts
            WHERE user_id=%s AND day=%s
            ORDER BY cnt DESC
            LIMIT 1
            """, (user_id, day))
            row = cur.fetchone()
            return row or {}


def first_purchase_eligible(user_id: int) -> bool:
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT has_paid, first_purchase_used FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone() or {}
            return (not row.get("has_paid")) and (not row.get("first_purchase_used"))

def mark_first_purchase_used(user_id: int):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET first_purchase_used=TRUE WHERE user_id=%s", (user_id,))
        conn.commit()


def get_ab_variant(user_id: int, experiment: str, default_variant: str = "control") -> str:
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT variant FROM ab_assignments WHERE user_id=%s AND experiment=%s", (user_id, experiment))
            row = cur.fetchone()
            return (row or {}).get("variant") or default_variant

def set_ab_variant(user_id: int, experiment: str, variant: str):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO ab_assignments (user_id, experiment, variant)
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id, experiment) DO UPDATE SET variant=EXCLUDED.variant
            """, (user_id, experiment, variant))
        conn.commit()

def log_offer_event(user_id: int, event: str, offer_key: str, variant: str | None = None, meta: dict | None = None):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO offer_events (user_id, event, offer_key, variant, meta)
            VALUES (%s,%s,%s,%s,%s)
            """, (user_id, event, offer_key, variant, json.dumps(meta) if meta else None))
        conn.commit()

def get_offer_stats(days: int = 7):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT offer_key, COALESCE(variant,'') as variant,
                   SUM(CASE WHEN event='impression' THEN 1 ELSE 0 END) AS impressions,
                   SUM(CASE WHEN event='click' THEN 1 ELSE 0 END) AS clicks,
                   SUM(CASE WHEN event='purchase' THEN 1 ELSE 0 END) AS purchases,
                   SUM(CASE WHEN event='bonus_applied' THEN 1 ELSE 0 END) AS bonuses
            FROM offer_events
            WHERE ts >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY offer_key, COALESCE(variant,'')
            ORDER BY purchases DESC, clicks DESC, impressions DESC
            """, (days,))
            return cur.fetchall() or []



def get_experiment_winner(experiment: str) -> str | None:
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT winner FROM experiment_winners WHERE experiment=%s", (experiment,))
            row = cur.fetchone()
            return (row or {}).get("winner")

def set_experiment_winner(experiment: str, winner: str):
    init_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO experiment_winners (experiment, winner)
            VALUES (%s,%s)
            ON CONFLICT (experiment) DO UPDATE SET winner=EXCLUDED.winner, updated_at=NOW()
            """, (experiment, winner))
        conn.commit()

def get_experiment_stats(experiment: str, days: int = 7):
    """Return per-variant stats using offer_events."""
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT COALESCE(variant,'') AS variant,
                   SUM(CASE WHEN event='impression' THEN 1 ELSE 0 END) AS impressions,
                   SUM(CASE WHEN event='click' THEN 1 ELSE 0 END) AS clicks,
                   SUM(CASE WHEN event='purchase' THEN 1 ELSE 0 END) AS purchases,
                   COALESCE(SUM(CASE WHEN event='purchase' THEN (meta->>'stars')::INT ELSE 0 END),0) AS stars
            FROM offer_events
            WHERE offer_key=%s
              AND ts >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY COALESCE(variant,'')
            ORDER BY stars DESC, purchases DESC, clicks DESC, impressions DESC
            """, (experiment, days))
            return cur.fetchall() or []


def add_history(user_id: int, kind: str, prompt: str, response: str, subject: str | None = None):
    """Store last user interactions for UX (history view)."""
    init_db()
    # Keep response small to avoid DB bloat
    prompt = (prompt or "")[:2000]
    response = (response or "")[:4000]
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_history (user_id, kind, subject, prompt, response)
                   VALUES (%s,%s,%s,%s,%s)""",
                (user_id, kind, subject, prompt, response),
            )
            # Soft trim: keep last 200 rows per user
            cur.execute(
                """DELETE FROM user_history
                   WHERE id IN (
                     SELECT id FROM user_history
                     WHERE user_id=%s
                     ORDER BY id DESC
                     OFFSET 200
                   )""",
                (user_id,),
            )

def list_history(user_id: int, limit: int = 10):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, kind, subject, prompt, response, created_at
                   FROM user_history
                   WHERE user_id=%s
                   ORDER BY id DESC
                   LIMIT %s""",
                (user_id, limit),
            )
            return cur.fetchall()


def list_history_subjects(user_id: int, limit: int = 8):
    """Return most frequent subjects from recent history for UX filtering."""
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT subject, COUNT(*) AS cnt
                   FROM (
                     SELECT subject
                     FROM user_history
                     WHERE user_id=%s AND subject IS NOT NULL AND subject <> ''
                     ORDER BY id DESC
                     LIMIT 200
                   ) s
                   GROUP BY subject
                   ORDER BY cnt DESC, subject ASC
                   LIMIT %s""",
                (user_id, limit),
            )
            return cur.fetchall()

def list_history_filtered(user_id: int, subject: str | None = None, limit: int = 10):
    init_db()
    with _conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if subject and subject != "__all__":
                cur.execute(
                    """SELECT id, kind, subject, prompt, response, created_at
                       FROM user_history
                       WHERE user_id=%s AND subject=%s
                       ORDER BY id DESC
                       LIMIT %s""",
                    (user_id, subject, limit),
                )
            else:
                cur.execute(
                    """SELECT id, kind, subject, prompt, response, created_at
                       FROM user_history
                       WHERE user_id=%s
                       ORDER BY id DESC
                       LIMIT %s""",
                    (user_id, limit),
                )
            return cur.fetchall()
