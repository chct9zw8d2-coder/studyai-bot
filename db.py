def init_db():
    with _conn() as conn:
        with conn.cursor() as cur:

            # ----------------
            # USERS
            # ----------------
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
              paywall_count INT DEFAULT 0,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            # Ensure migration-safe fields
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS paywall_count INT DEFAULT 0;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS grade_photo_trial_used BOOLEAN DEFAULT FALSE;")


            # ----------------
            # DAILY USAGE
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
              user_id BIGINT NOT NULL,
              day DATE NOT NULL,
              text_used INT DEFAULT 0,
              img_used INT DEFAULT 0,
              text_bonus INT DEFAULT 0,
              img_bonus INT DEFAULT 0,
              song_used INT DEFAULT 0,
              song_bonus INT DEFAULT 0,
              PRIMARY KEY (user_id, day)
            );""")


            # ----------------
            # PAYMENTS
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
              id SERIAL PRIMARY KEY,
              user_id BIGINT NOT NULL,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              stars INT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")


            # ----------------
            # USER HISTORY
            # ----------------
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

            cur.execute("ALTER TABLE user_history ADD COLUMN IF NOT EXISTS subject TEXT NULL;")


            # ----------------
            # PAYOUTS
            # ----------------
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


            # ----------------
            # ACTIVITY COUNTS (NEW SYSTEM)
            # ----------------
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


            # ----------------
            # OFFER EVENTS
            # ----------------
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


            # ----------------
            # AB TESTING
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS ab_assignments (
              user_id BIGINT NOT NULL,
              experiment TEXT NOT NULL,
              variant TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT NOW(),
              PRIMARY KEY (user_id, experiment)
            );""")


            cur.execute("""
            CREATE TABLE IF NOT EXISTS experiment_winners (
              experiment TEXT PRIMARY KEY,
              winner TEXT NOT NULL,
              updated_at TIMESTAMP DEFAULT NOW()
            );""")


            # ----------------
            # PROMOS
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS promos (
              user_id BIGINT PRIMARY KEY,
              promo_kind TEXT NOT NULL,
              target_plan TEXT NOT NULL,
              expires_at TIMESTAMP NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")


            # ----------------
            # TEXT CACHE
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS text_cache (
              key TEXT PRIMARY KEY,
              response TEXT NOT NULL,
              model TEXT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              hits INT DEFAULT 0
            );""")


            # ----------------
            # IMAGE CACHE (legacy safe)
            # ----------------
            cur.execute("""
            CREATE TABLE IF NOT EXISTS image_cache (
              key TEXT PRIMARY KEY,
              telegram_file_id TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              hits INT DEFAULT 0
            );""")


        conn.commit()
