from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from trading_signal_bot.database.database import Database
from trading_signal_bot.health.server import HealthServer
from trading_signal_bot.strategy.indicators import ema, macd, rsi, sma
from trading_signal_bot.utils.time import display_datetime, gregorian_to_jalali


class IndicatorTests(unittest.TestCase):
    def test_indicators_return_expected_shapes(self) -> None:
        values = list(range(1, 80))
        self.assertEqual(len(sma(values, 10)), len(values))
        self.assertEqual(len(ema(values, 10)), len(values))
        self.assertEqual(len(rsi(values)), len(values))
        line, signal, histogram = macd(values)
        self.assertEqual((len(line), len(signal), len(histogram)), (len(values),) * 3)
        self.assertIsNotNone(line[-1])


class DatabaseTests(unittest.TestCase):
    def test_access_and_duplicate_signal_are_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(str(Path(directory) / "test.db"))
            database.upsert_user(123, "tester", "آزمایشی")
            self.assertFalse(database.is_allowed(123))
            database.set_allowed(123, True)
            self.assertTrue(database.is_allowed(123))
            candidate = {
                "dedupe_key": "BTCUSDT:LONG:test",
                "symbol": "BTCUSDT",
                "signal_type": "LONG",
                "entry_price": 100.0,
                "stop_loss": 99.0,
                "take_profit": 102.0,
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "score": 8,
                "reason": "آزمایش",
            }
            self.assertIsNotNone(database.create_signal(candidate))
            self.assertIsNone(database.create_signal(candidate))
            self.assertEqual(len(database.active_signals()), 1)
            database.close()


class DateTests(unittest.TestCase):
    def test_persian_date_and_digits(self) -> None:
        self.assertEqual(gregorian_to_jalali(2026, 9, 23), (1405, 7, 1))
        date, clock = display_datetime(
            datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc), "Asia/Tehran"
        )
        self.assertEqual(date, "۱۴۰۵/۰۷/۰۱")
        self.assertTrue(clock.startswith("۱۵:"))


class HealthTests(unittest.TestCase):
    def test_health_endpoint_returns_safe_payload(self) -> None:
        server = HealthServer("127.0.0.1", 0)
        server.start()
        port = server.server.server_address[1]
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'{"status": "ok"}')
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
