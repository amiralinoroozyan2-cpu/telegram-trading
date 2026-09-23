from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def access_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔑 درخواست دسترسی", callback_data="request_access")]]
    )


def access_review_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تایید دسترسی", callback_data=f"allow_user:{telegram_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد درخواست", callback_data=f"deny_user:{telegram_id}"
                ),
            ]
        ]
    )
