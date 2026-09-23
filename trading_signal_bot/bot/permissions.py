from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from trading_signal_bot.config.settings import Settings
from trading_signal_bot.database.database import Database


def user_id(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


def is_owner(update: Update, settings: Settings) -> bool:
    return user_id(update) == settings.owner_telegram_id


def is_allowed(update: Update, database: Database, settings: Settings) -> bool:
    current_id = user_id(update)
    return bool(current_id and (current_id == settings.owner_telegram_id or database.is_allowed(current_id)))


async def require_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings: Settings = context.application.bot_data["settings"]
    if not is_owner(update, settings):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ این دستور فقط برای مالک ربات فعال است.")
        return False
    return True


async def require_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings: Settings = context.application.bot_data["settings"]
    database: Database = context.application.bot_data["database"]
    if not is_allowed(update, database, settings):
        if update.effective_message:
            await update.effective_message.reply_text("🔒 دسترسی شما به این بخش فعال نیست.")
        return False
    return True
