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
        # миграция для БД, созданных до появления интервалов
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(subscriptions)")}
        if "interval_min" not in cols:
            conn.execute("ALTER TABLE subscriptions ADD COLUMN interval_min INTEGER NOT NULL DEFAULT 60")
        if "next_run_at" not in cols:
            conn.execute("ALTER TABLE subscriptions ADD COLUMN next_run_at TEXT")


def add(chat_id: int, dep: str, arr: str, trip_date: str, interval_min: int) -> bool:
    """True — подписка новая; False — такая уже была, ей обновлён интервал."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO subscriptions (chat_id, dep, arr, trip_date, interval_min) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, dep, arr, trip_date, interval_min),
        )
        if cur.rowcount == 1:
            return True      # next_run_at = NULL: первая рассылка на ближайшем тике
        conn.execute(
            "UPDATE subscriptions "
            "SET interval_min = ?, next_run_at = datetime(?, '+' || ? || ' minutes') "
            "WHERE chat_id = ? AND dep = ? AND arr = ? AND trip_date = ?",
            (interval_min, _now(), interval_min, chat_id, dep, arr, trip_date),
        )
        return False


def list_for_chat(chat_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE chat_id = ? ORDER BY trip_date", (chat_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def claim_due() -> list[dict]:
    """Забирает подписки, которым пора слать уведомление, и сразу сдвигает им next_run_at на их интервал.

    Сдвиг в той же транзакции защищает от двойной отправки, если задачи наложатся.
    """
    now = _now()
    conn = _connect()
    conn.isolation_level = None          # транзакцией управляем вручную
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE next_run_at IS NULL OR next_run_at <= ?", (now,)
        ).fetchall()
        conn.execute(
            "UPDATE subscriptions SET next_run_at = datetime(?, '+' || interval_min || ' minutes') "
            "WHERE next_run_at IS NULL OR next_run_at <= ?",
            (now, now),
        )
        conn.execute("COMMIT")
        return [dict(r) for r in rows]
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def postpone(sub_ids: list[int], minutes: int) -> None:
    """Перенести следующую отправку (например, когда бэкенд был недоступен)."""
    if not sub_ids:
        return
    marks = ",".join("?" * len(sub_ids))
    with closing(_connect()) as conn, conn:
        conn.execute(
            f"UPDATE subscriptions SET next_run_at = datetime(?, '+' || ? || ' minutes') "
            f"WHERE id IN ({marks})",
            (_now(), minutes, *sub_ids),
        )


def remove(sub_id: int, chat_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE id = ? AND chat_id = ?", (sub_id, chat_id))


def remove_chat(chat_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE chat_id = ?", (chat_id,))


def delete_expired(today_iso: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM subscriptions WHERE trip_date < ?", (today_iso,))