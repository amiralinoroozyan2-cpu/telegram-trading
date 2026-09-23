from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_signal_bot.market.data_provider import MarketCandle
from trading_signal_bot.strategy.indicators import ema, macd, rsi, sma, volume_ratio


@dataclass(frozen=True)
class SignalCandidate:
    symbol: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    score: int
    reason: str
    dedupe_key: str


class SignalStrategy:
    """A conservative long-only example strategy, not financial advice."""

    def analyze(self, symbol: str, candles: list[MarketCandle]) -> SignalCandidate | None:
        if len(candles) < 60:
            return None
        closes = [candle.close for candle in candles]
        volumes = [candle.volume for candle in candles]
        rsi_values = rsi(closes)
        ema_fast = ema(closes, 21)
        ema_slow = ema(closes, 50)
        sma_fast = sma(closes, 20)
        macd_line, macd_signal, _ = macd(closes)
        last = len(closes) - 1
        values = (rsi_values[last], ema_fast[last], ema_slow[last], sma_fast[last], macd_line[last], macd_signal[last])
        if any(value is None for value in values):
            return None
        rsi_value, fast, slow, simple, macd_value, signal_value = values
        volume = volume_ratio(volumes)
        score = 0
        reasons: list[str] = []
        if 45 <= rsi_value <= 70:
            score += 2
            reasons.append("وضعیت RSI مناسب است")
        if macd_value > signal_value:
            score += 2
            reasons.append("MACD تأیید شده است")
        if fast > slow:
            score += 2
            reasons.append("روند EMA صعودی است")
        if closes[-1] > simple:
            score += 1
            reasons.append("قیمت بالاتر از SMA قرار دارد")
        if volume is not None and volume >= 1.05:
            score += 2
            reasons.append("حجم معاملات افزایش یافته است")
        if closes[-1] > closes[-2]:
            score += 1
            reasons.append("حرکت اخیر قیمت مثبت است")
        if score < 6:
            return None

        entry = closes[-1]
        candle_key = candles[-1].timestamp.strftime("%Y%m%d%H%M")
        return SignalCandidate(
            symbol=symbol.upper(),
            signal_type="LONG",
            entry_price=entry,
            stop_loss=entry * 0.992,
            take_profit=entry * 1.015,
            entry_time=candles[-1].timestamp,
            score=score,
            reason=" | ".join(reasons),
            dedupe_key=f"{symbol.upper()}:LONG:{candle_key}",
        )

    @staticmethod
    def exit_status(
        signal: dict[str, object], current_price: float, now: datetime, expiry_hours: int
    ) -> str | None:
        entry_time = signal["entry_time"]
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        if entry_time.tzinfo is None:
            from datetime import timezone

            entry_time = entry_time.replace(tzinfo=timezone.utc)
        elapsed_hours = (now - entry_time).total_seconds() / 3600
        if current_price <= float(signal["stop_loss"]):
            return "STOPPED"
        if current_price >= float(signal["take_profit"]):
            return "CLOSED"
        if elapsed_hours >= expiry_hours:
            return "EXPIRED"
        return None
