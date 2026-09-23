from __future__ import annotations

from typing import Any

from trading_signal_bot.utils.time import display_datetime, format_price, to_persian_digits


def entry_message(signal: dict[str, Any], timezone_name: str) -> str:
    date, clock = display_datetime(signal["entry_time"], timezone_name)
    reasons = "\n".join(f"• {reason}" for reason in signal["reason"].split(" | "))
    return (
        "🟢 سیگنال جدید\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 ارز: {signal['symbol']}\n"
        f"📅 تاریخ: {date}\n"
        f"⏰ ساعت ورود: {clock}\n\n"
        f"💰 قیمت ورود: {format_price(signal['entry_price'])}\n"
        f"🎯 هدف: {format_price(signal['take_profit'])}\n"
        f"🛑 حد ضرر: {format_price(signal['stop_loss'])}\n\n"
        f"📊 امتیاز تحلیل: {to_persian_digits(signal['score'])} از ۱۰\n\n"
        f"📌 دلایل:\n{reasons}\n\n"
        "⚠️ این پیام نتیجه تحلیل خودکار بازار است و تضمین‌کننده سود نیست.\n"
        "━━━━━━━━━━━━━━"
    )


def exit_message(signal: dict[str, Any], timezone_name: str) -> str:
    entry_date, entry_clock = display_datetime(signal["entry_time"], timezone_name)
    exit_date, exit_clock = display_datetime(signal["exit_time"], timezone_name)
    pnl = float(signal["pnl_percent"] or 0)
    sign = "+" if pnl >= 0 else ""
    if signal["status"] == "STOPPED":
        title = "🔴 توقف سیگنال"
        result = f"📉 نتیجه: {to_persian_digits(f'{sign}{pnl:.2f}%')}"
    elif signal["status"] == "EXPIRED":
        title = "⚪ انقضای سیگنال"
        result = f"📊 نتیجه: {to_persian_digits(f'{sign}{pnl:.2f}%')}"
    else:
        title = "🔴 پایان سیگنال"
        result = f"📈 نتیجه: {to_persian_digits(f'{sign}{pnl:.2f}%')}"
    return (
        f"{title}\n"
        "━━━━━━━━━━━━━━\n"
        f"💎 ارز: {signal['symbol']}\n"
        f"📅 تاریخ ورود: {entry_date}\n"
        f"⏰ زمان ورود: {entry_clock}\n"
        f"📅 تاریخ خروج: {exit_date}\n"
        f"⏰ زمان خروج: {exit_clock}\n\n"
        f"💰 قیمت ورود: {format_price(signal['entry_price'])}\n"
        f"💰 قیمت خروج: {format_price(signal['exit_price'])}\n"
        f"{result}\n"
        "━━━━━━━━━━━━━━"
    )
