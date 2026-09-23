from __future__ import annotations

from typing import Any

from telegram import Bot, Update
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from trading_signal_bot.bot.keyboards import access_request_keyboard, access_review_keyboard
from trading_signal_bot.bot.permissions import require_allowed, require_owner, user_id
from trading_signal_bot.config.settings import Settings
from trading_signal_bot.database.database import Database
from trading_signal_bot.signals.manager import SignalManager, SignalPublisher
from trading_signal_bot.utils.formatting import entry_message, exit_message
from trading_signal_bot.utils.logger import get_logger
from trading_signal_bot.utils.time import display_datetime

logger = get_logger(__name__)


def _register_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    user = update.effective_user
    if not user:
        return {}
    database: Database = context.application.bot_data["database"]
    settings: Settings = context.application.bot_data["settings"]
    return database.upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name or "کاربر",
        is_owner=user.id == settings.owner_telegram_id,
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    record = _register_user(update, context)
    settings: Settings = context.application.bot_data["settings"]
    if record.get("is_owner") or record.get("is_allowed"):
        await update.effective_message.reply_text(
            "سلام. ربات تحلیل بازار فعال است.\nاز منوی دستورات برای مشاهده وضعیت و سیگنال‌ها استفاده کنید."
        )
        return
    await update.effective_message.reply_text(
        "🔒 دسترسی شما به این ربات فعال نیست.\n\nبرای درخواست دسترسی، روی دکمه زیر کلیک کنید.",
        reply_markup=access_request_keyboard(),
    )


async def request_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.from_user:
        return
    await query.answer("درخواست شما ثبت شد.")
    database: Database = context.application.bot_data["database"]
    settings: Settings = context.application.bot_data["settings"]
    database.upsert_user(query.from_user.id, query.from_user.username, query.from_user.first_name or "کاربر")
    database.mark_access_requested(query.from_user.id)
    request_time = database.get_user(query.from_user.id).get("access_requested_at", "نامشخص")  # type: ignore[union-attr]
    text = (
        "🔔 درخواست دسترسی جدید\n\n"
        f"نام: {query.from_user.full_name}\n"
        f"Username: @{query.from_user.username or 'ندارد'}\n"
        f"Telegram ID: {query.from_user.id}\n"
        f"زمان درخواست: {request_time}"
    )
    try:
        await context.bot.send_message(
            chat_id=settings.owner_telegram_id,
            text=text,
            reply_markup=access_review_keyboard(query.from_user.id),
        )
        await query.edit_message_text("درخواست شما برای مالک ربات ارسال شد.")
    except Exception:
        logger.exception("خطای ارسال درخواست دسترسی")
        await query.edit_message_text("ارسال درخواست با خطا مواجه شد. دوباره تلاش کنید.")


async def access_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    settings: Settings = context.application.bot_data["settings"]
    if query.from_user.id != settings.owner_telegram_id:
        await query.answer("دسترسی کافی ندارید.", show_alert=True)
        return
    database: Database = context.application.bot_data["database"]
    action, raw_id = query.data.split(":", 1)
    target_id = int(raw_id)
    database.set_allowed(target_id, action == "allow_user")
    await query.answer("انجام شد.")
    if action == "allow_user":
        await context.bot.send_message(chat_id=target_id, text="✅ دسترسی شما تایید شد. اکنون می‌توانید از ربات استفاده کنید.")
        await query.edit_message_text(f"✅ دسترسی کاربر {target_id} تایید شد.")
    else:
        await query.edit_message_text(f"❌ درخواست کاربر {target_id} رد شد.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_allowed(update, context):
        return
    settings: Settings = context.application.bot_data["settings"]
    database: Database = context.application.bot_data["database"]
    await update.effective_message.reply_text(
        "🟢 ربات فعال است.\n"
        f"⏱ فاصله بررسی: {settings.check_interval_seconds} ثانیه\n"
        f"💎 نماد بازار: {settings.market_symbol}\n"
        f"📌 سیگنال‌های فعال: {len(database.active_signals())}"
    )


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update, context):
        return
    database: Database = context.application.bot_data["database"]
    users = database.all_users()
    if not users:
        await update.effective_message.reply_text("هنوز کاربری ثبت نشده است.")
        return
    lines = ["👥 کاربران ثبت‌شده:"]
    for record in users:
        state = "مجاز" if record["is_allowed"] or record["is_owner"] else "غیرمجاز"
        lines.append(f"• {record['first_name']} | {record['telegram_id']} | {state}")
    await update.effective_message.reply_text("\n".join(lines))


async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update, context):
        return
    await _set_access_from_command(update, context, True)


async def deny_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update, context):
        return
    await _set_access_from_command(update, context, False)


async def _set_access_from_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, allowed: bool
) -> None:
    if not context.args:
        await update.effective_message.reply_text("شناسه تلگرام را بعد از دستور وارد کنید.")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("شناسه تلگرام باید عددی باشد.")
        return
    database: Database = context.application.bot_data["database"]
    if not database.get_user(target_id):
        await update.effective_message.reply_text("این کاربر هنوز با ربات تعامل نکرده است.")
        return
    database.set_allowed(target_id, allowed)
    await update.effective_message.reply_text("✅ دسترسی به‌روزرسانی شد." if allowed else "✅ دسترسی حذف شد.")
    if allowed:
        await context.bot.send_message(chat_id=target_id, text="✅ دسترسی شما تایید شد. اکنون می‌توانید از ربات استفاده کنید.")


async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_allowed(update, context):
        return
    database: Database = context.application.bot_data["database"]
    active = database.active_signals()
    if not active:
        await update.effective_message.reply_text("در حال حاضر سیگنال فعالی وجود ندارد.")
        return
    lines = ["📊 سیگنال‌های فعال:"]
    for signal in active:
        lines.append(
            f"• {signal['symbol']} | ورود: {signal['entry_price']:.4f} | "
            f"هدف: {signal['take_profit']:.4f} | حد ضرر: {signal['stop_loss']:.4f}"
        )
    await update.effective_message.reply_text("\n".join(lines))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update, context):
        return
    settings: Settings = context.application.bot_data["settings"]
    await update.effective_message.reply_text(
        "⚙️ تنظیمات فعال:\n"
        f"نماد: {settings.market_symbol}\n"
        f"بازه داده: {settings.market_interval}\n"
        f"فاصله بررسی: {settings.check_interval_seconds} ثانیه\n"
        f"منطقه زمانی: {settings.timezone}"
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("دستور شناخته نشد. از /start استفاده کنید.")


def build_application(settings: Settings, database: Database, manager: SignalManager) -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data.update(settings=settings, database=database, signal_manager=manager)
    application.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("status", status_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("users", users_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("allow", allow_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("deny", deny_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("signals", signals_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("settings", settings_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(request_access_callback, pattern="^request_access$"))
    application.add_handler(CallbackQueryHandler(access_review_callback, pattern="^(allow_user|deny_user):"))
    application.add_handler(MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, unknown_command))
    return application


class TelegramPublisher(SignalPublisher):
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings

    async def publish_entry(self, signal: dict[str, Any]) -> None:
        await self.bot.send_message(
            chat_id=self.settings.telegram_channel_id,
            text=entry_message(signal, self.settings.timezone),
        )

    async def publish_exit(self, signal: dict[str, Any]) -> None:
        await self.bot.send_message(
            chat_id=self.settings.telegram_channel_id,
            text=exit_message(signal, self.settings.timezone),
        )
