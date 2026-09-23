from __future__ import annotations

import asyncio

from trading_signal_bot.config.settings import Settings
from trading_signal_bot.market.data_provider import MarketDataProvider
from trading_signal_bot.signals.manager import SignalManager
from trading_signal_bot.utils.logger import get_logger

logger = get_logger(__name__)


class MarketScheduler:
    def __init__(
        self,
        settings: Settings,
        provider: MarketDataProvider,
        manager: SignalManager,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.manager = manager
        self.stop_event = asyncio.Event()

    async def run_once(self) -> None:
        try:
            logger.info("شروع بررسی بازار: %s", self.settings.market_symbol)
            candles = await self.provider.fetch_candles(
                self.settings.market_symbol,
                self.settings.market_interval,
                self.settings.market_limit,
            )
            logger.info("داده بازار دریافت شد: %s کندل", len(candles))
            await self.manager.process_market(self.settings.market_symbol, candles)
        except Exception:
            logger.exception("خطا در چرخه بررسی بازار؛ برنامه ادامه می‌دهد.")

    async def run_forever(self) -> None:
        while not self.stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self.stop_event.wait(), timeout=self.settings.check_interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        self.stop_event.set()
