from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

from trading_signal_bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MarketCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    async def fetch_candles(self, symbol: str, interval: str, limit: int) -> list[MarketCandle]:
        ...


class BinancePublicMarketData:
    """Binance public REST API; no account or trading credentials are used."""

    endpoint = "https://api.binance.com/api/v3/klines"

    def __init__(self, timeout_seconds: float = 15.0, retries: int = 3) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    async def fetch_candles(self, symbol: str, interval: str, limit: int) -> list[MarketCandle]:
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(self.endpoint, params=params)
                    response.raise_for_status()
                    payload = response.json()
                return [
                    MarketCandle(
                        timestamp=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                    )
                    for row in payload
                ]
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                last_error = exc
                logger.warning("خطای دریافت داده بازار، تلاش %s از %s", attempt, self.retries)
                if attempt < self.retries:
                    await asyncio.sleep(min(2**attempt, 8))
        raise RuntimeError("دریافت داده بازار پس از چند تلاش ناموفق بود.") from last_error
