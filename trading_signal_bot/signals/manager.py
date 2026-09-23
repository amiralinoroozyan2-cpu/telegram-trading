from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from trading_signal_bot.database.database import Database
from trading_signal_bot.market.data_provider import MarketCandle
from trading_signal_bot.strategy.strategy import SignalCandidate, SignalStrategy
from trading_signal_bot.utils.logger import get_logger

logger = get_logger(__name__)


class SignalPublisher(Protocol):
    async def publish_entry(self, signal: dict[str, Any]) -> None:
        ...

    async def publish_exit(self, signal: dict[str, Any]) -> None:
        ...


class SignalManager:
    def __init__(
        self,
        database: Database,
        strategy: SignalStrategy,
        publisher: SignalPublisher | None = None,
        expiry_hours: int = 24,
    ) -> None:
        self.database = database
        self.strategy = strategy
        self.publisher = publisher
        self.expiry_hours = expiry_hours

    async def process_market(
        self, symbol: str, candles: list[MarketCandle], now: datetime | None = None
    ) -> None:
        current_time = now or datetime.now(timezone.utc)
        candidate = self.strategy.analyze(symbol, candles)
        current_price = candles[-1].close if candles else None
        if current_price is None:
            return

        await self._process_active(current_price, current_time)
        if not candidate:
            return
        signal_id = self.database.create_signal(self._candidate_payload(candidate))
        if signal_id is None:
            logger.info("سیگنال تکراری نادیده گرفته شد: %s", candidate.symbol)
            return
        signal = self.database.get_signal(signal_id)
        if signal and self.publisher and self.database.add_event(signal_id, "ENTRY_SENT"):
            try:
                await self.publisher.publish_entry(signal)
            except Exception:
                logger.exception("خطای انتشار پیام ورود در تلگرام")
                # Remove the marker so the next scheduled scan can retry.
                self.database.remove_event(signal_id, "ENTRY_SENT")

    async def _process_active(self, current_price: float, now: datetime) -> None:
        for active in self.database.active_signals():
            status = self.strategy.exit_status(active, current_price, now, self.expiry_hours)
            if not status:
                continue
            closed = self.database.close_signal(
                int(active["id"]), status, current_price, now
            )
            if not closed or not self.publisher or self.database.has_event(int(active["id"]), "EXIT_SENT"):
                continue
            if self.database.add_event(int(active["id"]), "EXIT_SENT"):
                try:
                    await self.publisher.publish_exit(closed)
                except Exception:
                    logger.exception("خطای انتشار پیام خروج در تلگرام")

    @staticmethod
    def _candidate_payload(candidate: SignalCandidate) -> dict[str, Any]:
        return {
            "dedupe_key": candidate.dedupe_key,
            "symbol": candidate.symbol,
            "signal_type": candidate.signal_type,
            "entry_price": candidate.entry_price,
            "stop_loss": candidate.stop_loss,
            "take_profit": candidate.take_profit,
            "entry_time": candidate.entry_time.isoformat(),
            "score": candidate.score,
            "reason": candidate.reason,
        }
