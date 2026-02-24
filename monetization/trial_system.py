
from datetime import datetime, timedelta

TRIAL_DAYS = 7

def trial_available(user_row):
    if not user_row:
        return True
    return not bool(user_row.get("trial_used"))

def activate_trial(db_conn, user_id):
    with db_conn.cursor() as cur:
        cur.execute("""
        UPDATE users
        SET tariff='START',
            sub_until=%s,
            trial_used=TRUE
        WHERE user_id=%s
        """, (datetime.utcnow() + timedelta(days=TRIAL_DAYS), user_id))
        db_conn.commit()
