from __future__ import annotations

from typing import Sequence


def sma(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if period <= 0:
        raise ValueError("period must be positive")
    for index in range(period - 1, len(values)):
        window = values[index - period + 1 : index + 1]
        result[index] = sum(window) / period
    return result


def ema(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return result
    current = sum(values[:period]) / period
    result[period - 1] = current
    multiplier = 2 / (period + 1)
    for index in range(period, len(values)):
        current = (values[index] - current) * multiplier + current
        result[index] = current
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    result[period] = 100.0 if average_loss == 0 else 100 - 100 / (1 + average_gain / average_loss)
    for index in range(period + 1, len(values)):
        gain = gains[index - 1]
        loss = losses[index - 1]
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        result[index] = 100.0 if average_loss == 0 else 100 - 100 / (1 + average_gain / average_loss)
    return result


def macd(
    values: Sequence[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast = ema(values, fast_period)
    slow = ema(values, slow_period)
    line: list[float | None] = [None] * len(values)
    compact: list[float] = []
    compact_indices: list[int] = []
    for index, (fast_value, slow_value) in enumerate(zip(fast, slow)):
        if fast_value is not None and slow_value is not None:
            line[index] = fast_value - slow_value
            compact.append(line[index])
            compact_indices.append(index)
    compact_signal = ema(compact, signal_period)
    signal: list[float | None] = [None] * len(values)
    histogram: list[float | None] = [None] * len(values)
    for compact_index, original_index in enumerate(compact_indices):
        if compact_signal[compact_index] is not None:
            signal[original_index] = compact_signal[compact_index]
            histogram[original_index] = line[original_index] - signal[original_index]  # type: ignore[operator]
    return line, signal, histogram


def volume_ratio(volumes: Sequence[float], period: int = 20) -> float | None:
    if len(volumes) < period + 1:
        return None
    average = sum(volumes[-period - 1 : -1]) / period
    return volumes[-1] / average if average else None
