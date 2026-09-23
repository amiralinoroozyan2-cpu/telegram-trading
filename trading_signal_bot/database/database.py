from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_signal_bot.utils.logger import get_logger
from trading_signal_bot.utils.time import iso_utc

logger = get_logger(__name__)


class Database:
    def __init__(self, path: str) -> None:
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.initialize()

    def initialize(self) -> None:
        with self.lock, self.connection:
            self.connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    is_allowed INTEGER NOT NULL DEFAULT 0,
                    is_owner INTEGER NOT NULL DEFAULT 0,
                    access_requested_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedupe_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    status TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    score INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    pnl_percent REAL,
                    created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_active_signal_dedupe
                    ON signals(dedupe_key) WHERE status = 'ACTIVE';
                CREATE TABLE IF NOT EXISTS signal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER NOT NULL REFERENCES signals(id),
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(signal_id, event_type)
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        is_owner: bool = False,
    ) -> dict[str, Any]:
        now = iso_utc()
        with self.lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO users (telegram_id, username, first_name, is_owner, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    is_owner=MAX(users.is_owner, excluded.is_owner),
                    updated_at=excluded.updated_at
                """,
                (telegram_id, username, first_name, int(is_owner), now, now),
            )
            row = self.connection.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        return self._row(row) or {}

    def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        return self._row(row)

    def is_allowed(self, telegram_id: int) -> bool:
        user = self.get_user(telegram_id)
        return bool(user and (user["is_allowed"] or user["is_owner"]))

    def set_allowed(self, telegram_id: int, allowed: bool) -> None:
        now = iso_utc()
        with self.lock, self.connection:
            self.connection.execute(
                """
                UPDATE users SET is_allowed = ?, access_requested_at = NULL, updated_at = ?
                WHERE telegram_id = ?
                """,
                (int(allowed), now, telegram_id),
            )

    def mark_access_requested(self, telegram_id: int) -> None:
        with self.lock, self.connection:
            self.connection.execute(
                "UPDATE users SET access_requested_at = ?, updated_at = ? WHERE telegram_id = ?",
                (iso_utc(), iso_utc(), telegram_id),
            )

    def pending_users(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute(
                """
                SELECT * FROM users
                WHERE is_allowed = 0 AND is_owner = 0 AND access_requested_at IS NOT NULL
                ORDER BY access_requested_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def all_users(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def create_signal(self, candidate: dict[str, Any]) -> int | None:
        now = iso_utc()
        with self.lock, self.connection:
            try:
                cursor = self.connection.execute(
                    """
                    INSERT INTO signals (
                        dedupe_key, symbol, type, entry_price, stop_loss, take_profit,
                        status, entry_time, score, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)
                    """,
                    (
                        candidate["dedupe_key"],
                        candidate["symbol"],
                        candidate["signal_type"],
                        candidate["entry_price"],
                        candidate["stop_loss"],
                        candidate["take_profit"],
                        candidate["entry_time"],
                        candidate["score"],
                        candidate["reason"],
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                return None
        logger.info("سیگنال جدید ثبت شد: %s", candidate["symbol"])
        return cursor.lastrowid

    def get_signal(self, signal_id: int) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT * FROM signals WHERE id = ?", (signal_id,)
            ).fetchone()
        return self._row(row)

    def active_signals(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM signals WHERE status = 'ACTIVE' ORDER BY entry_time ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def close_signal(
        self, signal_id: int, status: str, exit_price: float, exit_time: datetime
    ) -> dict[str, Any] | None:
        if status not in {"CLOSED", "STOPPED", "EXPIRED"}:
            raise ValueError("وضعیت خروج نامعتبر است.")
        with self.lock, self.connection:
            signal = self.get_signal(signal_id)
            if not signal or signal["status"] != "ACTIVE":
                return None
            entry = float(signal["entry_price"])
            pnl = ((exit_price - entry) / entry) * 100
            self.connection.execute(
                """
                UPDATE signals
                SET status = ?, exit_price = ?, exit_time = ?, pnl_percent = ?
                WHERE id = ? AND status = 'ACTIVE'
                """,
                (status, exit_price, iso_utc(exit_time), pnl, signal_id),
            )
            return self.get_signal(signal_id)

    def has_event(self, signal_id: int, event_type: str) -> bool:
        with self.lock:
            row = self.connection.execute(
                "SELECT 1 FROM signal_events WHERE signal_id = ? AND event_type = ?",
                (signal_id, event_type),
            ).fetchone()
        return row is not None

    def add_event(self, signal_id: int, event_type: str, payload: str | None = None) -> bool:
        with self.lock, self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO signal_events (signal_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (signal_id, event_type, payload, iso_utc()),
            )
        return cursor.rowcount == 1

    def remove_event(self, signal_id: int, event_type: str) -> None:
        with self.lock, self.connection:
            self.connection.execute(
                "DELETE FROM signal_events WHERE signal_id = ? AND event_type = ?",
                (signal_id, event_type),
            )

    def close(self) -> None:
        with self.lock:
            self.connection.close()
