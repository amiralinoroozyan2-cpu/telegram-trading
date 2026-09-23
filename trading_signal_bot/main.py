from __future__ import annotations

import asyncio
import signal

from trading_signal_bot.bot.handlers import TelegramPublisher, build_application
from trading_signal_bot.config.settings import Settings
from trading_signal_bot.database.database import Database
from trading_signal_bot.health.server import HealthServer
from trading_signal_bot.market.data_provider import BinancePublicMarketData
from trading_signal_bot.scheduler.scheduler import MarketScheduler
from trading_signal_bot.signals.manager import SignalManager
from trading_signal_bot.strategy.strategy import SignalStrategy
from trading_signal_bot.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


async def run() -> None:
    settings = Settings.from_env()
    database = Database(settings.database_path)
    health = HealthServer("0.0.0.0", settings.port)
    provider = BinancePublicMarketData()
    manager = SignalManager(
        database=database,
        strategy=SignalStrategy(),
        expiry_hours=settings.signal_expiry_hours,
    )
    application = build_application(settings, database, manager)
    manager.publisher = TelegramPublisher(application.bot, settings)
    scheduler = MarketScheduler(settings, provider, manager)
    shutdown_event = asyncio.Event()

    def request_shutdown() -> None:
        logger.info("درخواست توقف سرویس دریافت شد.")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(stop_signal, request_shutdown)
        except NotImplementedError:  # pragma: no cover - Windows fallback
            pass

    health.start()
    await application.initialize()
    await application.start()
    if application.updater is None:
        raise RuntimeError("راه‌اندازی دریافت پیام‌های تلگرام ناموفق بود.")
    await application.updater.start_polling(drop_pending_updates=True)
    scheduler_task = asyncio.create_task(scheduler.run_forever(), name="market-scheduler")
    logger.info("ربات با موفقیت راه‌اندازی شد.")
    try:
        await shutdown_event.wait()
    finally:
        scheduler.stop()
        await scheduler_task
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        health.stop()
        database.close()
        logger.info("ربات متوقف شد.")


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("ربات توسط کاربر متوقف شد.")


if __name__ == "__main__":
    main()
