"""
SilverTrade AI - Technical Indicators Module
=============================================
Provides real technical indicator calculations used by the AI decision engine.
"""

import math
from typing import List, Optional, Tuple


def sma(data: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average."""
    result: List[Optional[float]] = [None] * len(data)
    for i in range(period - 1, len(data)):
        result[i] = sum(data[i - period + 1 : i + 1]) / period
    return result


def ema(data: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average."""
    result: List[Optional[float]] = [None] * len(data)
    multiplier = 2 / (period + 1)
    sma_val = sum(data[:period]) / period
    result[period - 1] = sma_val
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def rsi(data: List[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index."""
    result: List[Optional[float]] = [None] * len(data)
    if len(data) < period + 1:
        return result

    gains, losses = [], []
    for i in range(1, period + 1):
        diff = data[i] - data[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period, len(data)):
        diff = data[i] - data[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))

    return result


def macd(
    data: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """MACD (Moving Average Convergence Divergence).

    Returns (macd_line, signal_line, histogram).
    """
    macd_line = ema(data, fast)
    signal_line_vals: List[Optional[float]] = [None] * len(data)

    # Convert EMA lists to proper MACD line
    macd_vals: List[Optional[float]] = [None] * len(data)
    slow_ema = ema(data, slow)

    for i in range(len(data)):
        if macd_line[i] is not None and slow_ema[i] is not None:
            macd_vals[i] = macd_line[i] - slow_ema[i]

    # Signal line is EMA of MACD line
    macd_clean: List[float] = [v for v in macd_vals if v is not None]
    if macd_clean:
        sig = ema(macd_clean, signal)
        sig_idx = 0
        for i in range(len(data)):
            if macd_vals[i] is not None:
                if sig_idx < len(sig) and sig[sig_idx] is not None:
                    signal_line_vals[i] = sig[sig_idx]
                sig_idx += 1

    histogram: List[Optional[float]] = [None] * len(data)
    for i in range(len(data)):
        if macd_vals[i] is not None and signal_line_vals[i] is not None:
            histogram[i] = macd_vals[i] - signal_line_vals[i]

    return macd_vals, signal_line_vals, histogram


def bollinger_bands(
    data: List[float], period: int = 20, std_dev: float = 2.0
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Bollinger Bands. Returns (middle, upper, lower)."""
    middle = sma(data, period)
    upper: List[Optional[float]] = [None] * len(data)
    lower: List[Optional[float]] = [None] * len(data)

    for i in range(period - 1, len(data)):
        window = data[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)
        upper[i] = middle[i] + std_dev * std if middle[i] is not None else None
        lower[i] = middle[i] - std_dev * std if middle[i] is not None else None

    return middle, upper, lower


def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[Optional[float]]:
    """Average True Range."""
    result: List[Optional[float]] = [None] * len(close)
    if len(close) < 2:
        return result

    tr_values: List[float] = []
    for i in range(1, len(close)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr_values.append(max(hl, hc, lc))

    if len(tr_values) < period:
        return result

    atr_val = sum(tr_values[:period]) / period
    result[period] = atr_val
    for i in range(period + 1, len(close)):
        atr_val = (atr_val * (period - 1) + tr_values[i - 1]) / period
        result[i] = atr_val

    return result
