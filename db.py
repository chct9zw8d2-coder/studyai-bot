\
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Optional

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL env var (Railway Postgres provides it)")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class UserState:
    user_id: int
    plan: str
    sub_expires_at: Optional[datetime]
    text_used_today: int
    img_used_today: int
    addon_text_left: int
    addon_img_left: int
    last_reset_date: date
    mode: str

class DB:
    def __init__(self) -> None:
        self.dsn = DATABASE_URL

    def _conn(self):
        return psycopg2.connect(self.dsn)

    def migrate(self) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    plan TEXT NOT NULL DEFAULT 'free',
                    sub_expires_at TIMESTAMPTZ NULL,
                    text_used_today INT NOT NULL DEFAULT 0,
                    img_used_today INT NOT NULL DEFAULT 0,
                    addon_text_left INT NOT NULL DEFAULT 0,
                    addon_img_left INT NOT NULL DEFAULT 0,
                    last_reset_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    mode TEXT NOT NULL DEFAULT 'idle',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            conn.commit()

    def ensure_user(self, user_id: int) -> UserState:
        self.migrate()
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO users(user_id) VALUES (%s)", (user_id,))
                conn.commit()
                cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
                row = cur.fetchone()
            return self._row_to_state(row)

    def get_user(self, user_id: int) -> UserState:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            if not row:
                return self.ensure_user(user_id)
            return self._row_to_state(row)

    def _row_to_state(self, row) -> UserState:
        return UserState(
            user_id=int(row["user_id"]),
            plan=row["plan"],
            sub_expires_at=row["sub_expires_at"],
            text_used_today=int(row["text_used_today"]),
            img_used_today=int(row["img_used_today"]),
            addon_text_left=int(row["addon_text_left"]),
            addon_img_left=int(row["addon_img_left"]),
            last_reset_date=row["last_reset_date"],
            mode=row["mode"],
        )

    def set_mode(self, user_id: int, mode: str) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE users SET mode=%s, updated_at=NOW() WHERE user_id=%s", (mode, user_id))
            conn.commit()

    def reset_daily(self, user_id: int, new_date: date) -> UserState:
        with self._conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE users
                SET text_used_today=0,
                    img_used_today=0,
                    addon_text_left=0,
                    addon_img_left=0,
                    last_reset_date=%s,
                    updated_at=NOW()
                WHERE user_id=%s
                RETURNING *;
                """,
                (new_date, user_id),
            )
            row = cur.fetchone()
            conn.commit()
            return self._row_to_state(row)

    def consume_text(self, user_id: int, n: int) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET text_used_today=text_used_today+%s, updated_at=NOW() WHERE user_id=%s",
                (n, user_id),
            )
            conn.commit()

    def consume_image(self, user_id: int, n: int) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET img_used_today=img_used_today+%s, updated_at=NOW() WHERE user_id=%s",
                (n, user_id),
            )
            conn.commit()

    def add_addons_today(self, user_id: int, text_add: int, img_add: int) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET addon_text_left=addon_text_left+%s,
                    addon_img_left=addon_img_left+%s,
                    updated_at=NOW()
                WHERE user_id=%s
                """,
                (text_add, img_add, user_id),
            )
            conn.commit()

    def set_subscription(self, user_id: int, plan: str, expires_at: datetime) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET plan=%s,
                    sub_expires_at=%s,
                    updated_at=NOW()
                WHERE user_id=%s
                """,
                (plan, expires_at, user_id),
            )
            conn.commit()
