import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

TICK_SECONDS = 60       # как часто beat проверяет, у кого подошло время рассылки
RETRY_DELAY_MIN = 5     # через сколько повторить, если бэкенд был недоступен

INTERVAL_CHOICES: list[tuple[int, str]] = [
    (15, "15 мин"),
    (30, "30 мин"),
    (60, "1 час"),
    (180, "3 часа"),
    (360, "6 часов"),
    (720, "12 часов"),
]
INTERVAL_LABELS = dict(INTERVAL_CHOICES)

DB_PATH = Path(__file__).resolve().parents[2] / "subscriptions.db"


def interval_label(minutes: int) -> str:
    return INTERVAL_LABELS.get(minutes, f"{minutes} мин")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER NOT NULL,
                dep          TEXT NOT NULL,
                arr          TEXT NOT NULL,
                trip_date    TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                interval_min INTEGER NOT NULL DEFAULT 60,
                next_run_at  TEXT,
                UNIQUE (chat_id, dep, arr, trip_date)
            )
            """
        )


def add(chat_id: int, dep: str, arr: str, trip_date: str) -> bool:
    """True, если подписка новая; False, если такая уже есть."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO subscriptions (chat_id, dep, arr, trip_date) VALUES (?, ?, ?, ?)",
            (chat_id, dep, arr, trip_date),
        )
        return cur.rowcount == 1


def list_for_chat(chat_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE chat_id = ? ORDER BY trip_date", (chat_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def all_active() -> list[dict]:
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM subscriptions").fetchall()]


def remove(sub_id: int, chat_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE id = ? AND chat_id = ?", (sub_id, chat_id))


def remove_chat(chat_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE chat_id = ?", (chat_id,))


def delete_expired(today_iso: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE trip_date < ?", (today_iso,))