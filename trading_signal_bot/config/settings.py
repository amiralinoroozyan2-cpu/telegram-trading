from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during static checks
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    owner_telegram_id: int
    telegram_channel_id: str
    timezone: str = "Asia/Tehran"
    check_interval_seconds: int = 300
    database_path: str = "signals.db"
    market_symbol: str = "BTCUSDT"
    market_interval: str = "5m"
    market_limit: int = 200
    signal_expiry_hours: int = 24
    port: int = 10000

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv()

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        owner = os.getenv("OWNER_TELEGRAM_ID", "").strip()
        channel = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
        missing = [
            name
            for name, value in (
                ("TELEGRAM_BOT_TOKEN", token),
                ("OWNER_TELEGRAM_ID", owner),
                ("TELEGRAM_CHANNEL_ID", channel),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"تنظیمات ضروری وارد نشده است: {', '.join(missing)}")

        try:
            owner_id = int(owner)
            interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
            port = int(os.getenv("PORT", "10000"))
            limit = int(os.getenv("MARKET_LIMIT", "200"))
            expiry = int(os.getenv("SIGNAL_EXPIRY_HOURS", "24"))
        except ValueError as exc:
            raise ValueError("مقادیر عددی تنظیمات معتبر نیستند.") from exc

        if interval < 30:
            raise ValueError("CHECK_INTERVAL_SECONDS باید حداقل 30 باشد.")
        if limit < 60:
            raise ValueError("MARKET_LIMIT باید حداقل 60 باشد.")
        return cls(
            telegram_bot_token=token,
            owner_telegram_id=owner_id,
            telegram_channel_id=channel,
            timezone=os.getenv("TIMEZONE", "Asia/Tehran"),
            check_interval_seconds=interval,
            database_path=os.getenv("DATABASE_PATH", "signals.db"),
            market_symbol=os.getenv("MARKET_SYMBOL", "BTCUSDT").upper(),
            market_interval=os.getenv("MARKET_INTERVAL", "5m"),
            market_limit=limit,
            signal_expiry_hours=expiry,
            port=port,
        )
