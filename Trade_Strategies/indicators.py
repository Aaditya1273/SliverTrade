"""
SilverTrade AI - Technical Indicators Module
=============================================
Provides real technical indicator calculations used by the AI decision engine.

SAFETY: All functions handle edge cases: empty lists, zero divisions,
NaN propagation, and None values gracefully.
"""

import logging
import math
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division returning default on zero/invalid denominator."""
    if denominator == 0 or denominator is None:
        return default
    try:
        result = numerator / denominator
        if result != result:  # NaN check
            return default
        return result
    except (ZeroDivisionError, TypeError, ValueError):
        return default


def sma(data: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average."""
    if not data or period <= 0 or len(data) < period:
        return [None] * len(data) if data else []
    result: List[Optional[float]] = [None] * len(data)
    for i in range(period - 1, len(data)):
        result[i] = _safe_div(sum(data[i - period + 1 : i + 1]), period)
    return result


def ema(data: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average."""
    if not data or period <= 0 or len(data) < period:
        return [None] * len(data) if data else []
    result: List[Optional[float]] = [None] * len(data)
    multiplier = _safe_div(2, period + 1)
    sma_val = _safe_div(sum(data[:period]), period)
    result[period - 1] = sma_val
    for i in range(period, len(data)):
        if result[i - 1] is not None and data[i] is not None:
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def rsi(data: List[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index."""
    result: List[Optional[float]] = [None] * len(data)
    if not data or len(data) < period + 1:
        return result

    gains, losses = [], []
    for i in range(1, period + 1):
        diff = data[i] - data[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    period_f = float(period)
    avg_gain = _safe_div(sum(gains), period_f)
    avg_loss = _safe_div(sum(losses), period_f)

    for i in range(period, len(data)):
        diff = data[i] - data[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = _safe_div((avg_gain * (period - 1) + gain), period_f)
        avg_loss = _safe_div((avg_loss * (period - 1) + loss), period_f)

        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = _safe_div(avg_gain, avg_loss)
            result[i] = 100 - _safe_div(100, (1 + rs), 100)

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
    n = len(data)
    macd_line = ema(data, fast)
    signal_line_vals: List[Optional[float]] = [None] * n

    # Convert EMA lists to proper MACD line
    macd_vals: List[Optional[float]] = [None] * n
    slow_ema = ema(data, slow)

    for i in range(n):
        if macd_line[i] is not None and slow_ema[i] is not None:
            macd_vals[i] = macd_line[i] - slow_ema[i]

    # Signal line is EMA of MACD line
    macd_clean: List[float] = [v for v in macd_vals if v is not None]
    if macd_clean:
        sig = ema(macd_clean, signal)
        sig_idx = 0
        for i in range(n):
            if macd_vals[i] is not None:
                if sig_idx < len(sig) and sig[sig_idx] is not None:
                    signal_line_vals[i] = sig[sig_idx]
                sig_idx += 1

    histogram: List[Optional[float]] = [None] * n
    for i in range(n):
        if macd_vals[i] is not None and signal_line_vals[i] is not None:
            histogram[i] = macd_vals[i] - signal_line_vals[i]

    return macd_vals, signal_line_vals, histogram


def bollinger_bands(
    data: List[float], period: int = 20, std_dev: float = 2.0
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Bollinger Bands. Returns (middle, upper, lower)."""
    n = len(data)
    middle = sma(data, period)
    upper: List[Optional[float]] = [None] * n
    lower: List[Optional[float]] = [None] * n

    for i in range(period - 1, n):
        window = data[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(max(variance, 0))  # Ensure non-negative for sqrt
        upper[i] = middle[i] + std_dev * std if middle[i] is not None else None
        lower[i] = middle[i] - std_dev * std if middle[i] is not None else None

    return middle, upper, lower


def adx(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[Optional[float]]:
    """Average Directional Index — measures trend strength.

    ADX > 25: strong trend. ADX < 20: weak/choppy.
    PlusDI > MinusDI: uptrend. MinusDI > PlusDI: downtrend.
    """
    n = len(close)
    result: List[Optional[float]] = [None] * n
    if n < period + 1:
        return result

    tr_values: List[float] = []
    plus_dm: List[float] = []
    minus_dm: List[float] = []

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr_values.append(max(hl, hc, lc))

        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0.0)
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0.0)

    if len(tr_values) < period:
        return result

    def _smooth(values, p):
        smoothed = [0.0] * len(values)
        smoothed[0] = sum(values[:p]) / p
        for j in range(1, len(values)):
            smoothed[j] = (smoothed[j - 1] * (p - 1) + values[j]) / p
        return smoothed

    atr_smooth = _smooth(tr_values, period)
    plus_smooth = _smooth(plus_dm, period)
    minus_smooth = _smooth(minus_dm, period)

    for i in range(period - 1, len(tr_values)):
        if atr_smooth[i] == 0:
            result[i + 1] = 0.0
            continue
        plus_di = 100 * plus_smooth[i] / atr_smooth[i]
        minus_di = 100 * minus_smooth[i] / atr_smooth[i]
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        result[i + 1] = dx

    return result


def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[Optional[float]]:
    """Average True Range."""
    n = len(close)
    result: List[Optional[float]] = [None] * n
    if n < 2:
        return result

    tr_values: List[float] = []
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr_values.append(max(hl, hc, lc))

    if len(tr_values) < period:
        return result

    period_f = float(period)
    atr_val = _safe_div(sum(tr_values[:period]), period_f)
    result[period] = atr_val
    for i in range(period + 1, n):
        atr_val = _safe_div((atr_val * (period - 1) + tr_values[i - 1]), period_f)
        result[i] = atr_val

    return result
