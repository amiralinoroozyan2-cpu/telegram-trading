from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_persian_digits(value: object) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to the Persian (Jalali) calendar."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + 365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        + gd
    )
    for index in range(gm - 1):
        days += g_days_in_month[index]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def display_datetime(value: datetime | str, timezone_name: str) -> tuple[str, str]:
    current = parse_utc(value) if isinstance(value, str) else value
    local = current.astimezone(ZoneInfo(timezone_name))
    year, month, day = gregorian_to_jalali(local.year, local.month, local.day)
    date = to_persian_digits(f"{year:04d}/{month:02d}/{day:02d}")
    clock = to_persian_digits(local.strftime("%H:%M:%S"))
    return date, clock


def format_price(value: float) -> str:
    if value >= 1000:
        rendered = f"{value:,.2f}".rstrip("0").rstrip(".")
    elif value >= 1:
        rendered = f"{value:.4f}".rstrip("0").rstrip(".")
    else:
        rendered = f"{value:.8f}".rstrip("0").rstrip(".")
    return to_persian_digits(rendered)
