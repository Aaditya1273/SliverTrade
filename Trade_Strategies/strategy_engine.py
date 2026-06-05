"""
SilverTrade AI - Strategy Decision Engine
==========================================
Analyzes market data using technical indicators and generates
trading signals with confidence scores and reasoning.
"""

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from indicators import atr, bollinger_bands, ema, macd, rsi, sma

logger = logging.getLogger(__name__)


class StrategyEngine:
    """AI-powered strategy engine that generates trading signals from market data.

    Uses a combination of technical indicators to evaluate market conditions
    and produce BUY/SELL/HOLD signals with confidence scores and explanations.

    SAFETY: All indicator calculations are wrapped in try/except. If any
    calculation fails, the engine returns a safe HOLD signal instead of crashing.
    """

    def __init__(self) -> None:
        self.name = "SilverTrade AI Strategy Engine"
        self.version = "1.0.0"

    def _safe_last(self, values: List[Optional[float]]) -> Optional[float]:
        """Get the last non-None value from a list."""
        if not values:
            return None
        for v in reversed(values):
            if v is not None:
                return v
        return None

    def _safe_div(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division that returns default instead of ZeroDivisionError or NaN."""
        if denominator == 0 or denominator is None:
            return default
        try:
            result = numerator / denominator
            if result != result:  # NaN check
                return default
            return result
        except (ZeroDivisionError, TypeError, ValueError):
            return default

    def _validate_data(self, ohlcv: List[Dict[str, Any]]) -> bool:
        """Validate that we have enough data for indicator calculations."""
        if not ohlcv or len(ohlcv) < 50:
            return False
        try:
            required = {"open", "high", "low", "close", "volume"}
            return all(k in ohlcv[0] for k in required)
        except (IndexError, KeyError, TypeError):
            return False

    def analyze(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
        """Analyze market data and return a trading signal.

        SAFETY: Entire body wrapped in try/except. On any calculation error,
        returns a safe HOLD signal instead of crashing the calling process.

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            ohlcv: List of OHLCV candles (most recent first or last)
            exchange: Exchange name

        Returns:
            Signal dict with decision, confidence, reasoning, or None if data insufficient
        """
        try:
            return self._analyze_impl(symbol, ohlcv, exchange)
        except Exception as e:
            logger.error(
                "StrategyEngine.analyze() crashed for %s: %s",
                symbol, traceback.format_exc(),
            )
            return {
                "symbol": symbol,
                "exchange": exchange,
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Analysis engine encountered error: {str(e)}. Holding position.",
                "price": 0.0,
                "indicators": {},
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _analyze_impl(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
        """Internal analysis implementation, split out so public analyze() wraps it in try/except."""
        if not self._validate_data(ohlcv):
            return None

        # Ensure data is sorted oldest → newest
        try:
            if ohlcv[0].get("time", 0) > ohlcv[-1].get("time", 0):
                ohlcv = list(reversed(ohlcv))
        except (IndexError, TypeError):
            return None

        closes = [c.get("close", 0.0) for c in ohlcv]
        highs = [c.get("high", 0.0) for c in ohlcv]
        lows = [c.get("low", 0.0) for c in ohlcv]
        volumes = [c.get("volume", 0) for c in ohlcv]

        # ── Calculate Indicators (each wrapped individually) ──────────
        rsi_vals: List[Optional[float]] = []
        ema_fast: List[Optional[float]] = []
        ema_slow: List[Optional[float]] = []
        ema_50: List[Optional[float]] = []
        macd_line: List[Optional[float]] = []
        signal_line: List[Optional[float]] = []
        bb_mid: List[Optional[float]] = []
        bb_upper: List[Optional[float]] = []
        bb_lower: List[Optional[float]] = []
        atr_vals: List[Optional[float]] = []
        sma_20: List[Optional[float]] = []
        sma_50: List[Optional[float]] = []

        try:
            rsi_vals = rsi(closes, 14)
        except Exception as e:
            logger.warning("RSI calculation failed: %s", e)
        try:
            ema_fast = ema(closes, 9)
        except Exception as e:
            logger.warning("EMA(9) calculation failed: %s", e)
        try:
            ema_slow = ema(closes, 21)
        except Exception as e:
            logger.warning("EMA(21) calculation failed: %s", e)
        try:
            ema_50 = ema(closes, 50)
        except Exception as e:
            logger.warning("EMA(50) calculation failed: %s", e)
        try:
            macd_line, signal_line, _ = macd(closes)
        except Exception as e:
            logger.warning("MACD calculation failed: %s", e)
        try:
            bb_mid, bb_upper, bb_lower = bollinger_bands(closes)
        except Exception as e:
            logger.warning("Bollinger Bands failed: %s", e)
        try:
            atr_vals = atr(highs, lows, closes)
        except Exception as e:
            logger.warning("ATR calculation failed: %s", e)
        try:
            sma_20 = sma(closes, 20)
        except Exception as e:
            logger.warning("SMA(20) calculation failed: %s", e)
        try:
            sma_50 = sma(closes, 50)
        except Exception as e:
            logger.warning("SMA(50) calculation failed: %s", e)

        # ── Extract Latest Values ─────────────────────────────────────
        latest_close = closes[-1] if closes else 0.0
        latest_rsi = self._safe_last(rsi_vals)
        latest_ema_fast = self._safe_last(ema_fast)
        latest_ema_slow = self._safe_last(ema_slow)
        latest_ema_50 = self._safe_last(ema_50)
        latest_macd = self._safe_last(macd_line)
        latest_signal = self._safe_last(signal_line)
        prev_macd = self._safe_last(macd_line[-3:-1] if len(macd_line) > 2 else macd_line)
        prev_signal = self._safe_last(signal_line[-3:-1] if len(signal_line) > 2 else signal_line)
        latest_bb_upper = self._safe_last(bb_upper)
        latest_bb_lower = self._safe_last(bb_lower)
        latest_atr = self._safe_last(atr_vals)
        latest_sma_20 = self._safe_last(sma_20)
        latest_sma_50 = self._safe_last(sma_50)
        latest_volume = volumes[-1] if volumes else 0
        avg_volume = self._safe_div(sum(volumes[-20:]), 20) if len(volumes) >= 20 else self._safe_div(sum(volumes), len(volumes)) if volumes else 0
        prev_close = closes[-2] if len(closes) > 1 else latest_close

        # ── Scoring System ────────────────────────────────────────────
        buy_score = 0
        sell_score = 0
        signals_found: List[str] = []
        max_score = 14

        # 1. RSI Analysis
        if latest_rsi is not None:
            if latest_rsi < 30:
                buy_score += 3
                signals_found.append(f"RSI oversold at {latest_rsi:.1f}")
            elif latest_rsi < 40:
                buy_score += 1
                signals_found.append(f"RSI approaching oversold ({latest_rsi:.1f})")
            elif latest_rsi > 70:
                sell_score += 3
                signals_found.append(f"RSI overbought at {latest_rsi:.1f}")
            elif latest_rsi > 60:
                sell_score += 1
                signals_found.append(f"RSI approaching overbought ({latest_rsi:.1f})")

        # 2. EMA Crossover (9/21)
        if latest_ema_fast is not None and latest_ema_slow is not None:
            if latest_ema_fast > latest_ema_slow:
                buy_score += 2
                signals_found.append("Bullish EMA cross (9 > 21)")
            else:
                sell_score += 2
                signals_found.append("Bearish EMA cross (9 < 21)")

        # 3. MACD Analysis
        if latest_macd is not None and latest_signal is not None:
            if latest_macd > latest_signal:
                buy_score += 1
                signals_found.append("MACD above signal")
            else:
                sell_score += 1
                signals_found.append("MACD below signal")
            if prev_macd is not None and prev_signal is not None:
                if latest_macd > latest_signal and prev_macd <= prev_signal:
                    buy_score += 2
                    signals_found.append("MACD bullish crossover")
                elif latest_macd < latest_signal and prev_macd >= prev_signal:
                    sell_score += 2
                    signals_found.append("MACD bearish crossover")

        # 4. Bollinger Bands
        if latest_close is not None and latest_bb_upper is not None and latest_bb_lower is not None:
            if latest_close <= latest_bb_lower:
                buy_score += 2
                signals_found.append("Price at lower Bollinger Band")
            elif latest_close >= latest_bb_upper:
                sell_score += 2
                signals_found.append("Price at upper Bollinger Band")

        # 5. Trend (Price vs SMA)
        if latest_sma_20 is not None and latest_sma_50 is not None:
            if latest_close > latest_sma_20:
                buy_score += 1
            else:
                sell_score += 1
            if latest_sma_20 > latest_sma_50:
                buy_score += 1
                signals_found.append("Golden cross (20 > 50 SMA)")
            else:
                sell_score += 1
                signals_found.append("Death cross (20 < 50 SMA)")

        # 6. Volume Confirmation
        volume_surge = latest_volume > avg_volume * 1.5
        price_up = latest_close > prev_close
        if volume_surge and price_up:
            buy_score += 1
            signals_found.append("Bullish volume surge")
        elif volume_surge and not price_up:
            sell_score += 1
            signals_found.append("Bearish volume surge")

        # 7. EMA Trend (50)
        if latest_ema_50 is not None:
            if latest_close > latest_ema_50:
                buy_score += 1
            else:
                sell_score += 1

        # ── Generate Decision ─────────────────────────────────────────
        net_score = buy_score - sell_score
        confidence_base = min(self._safe_div(abs(net_score), max_score) * 100, 95)
        volatility_factor = min(self._safe_div(latest_atr, latest_close, 0) * 100 if latest_atr and latest_close else 0, 5)
        confidence = min(confidence_base + volatility_factor, 99)

        if net_score >= 3:
            decision = "BUY"
            reasoning = f"Strong buy signal. {'. '.join(signals_found[:4])}."
        elif net_score >= 1:
            decision = "BUY"
            reasoning = f"Moderate buy opportunity. {'. '.join(signals_found[:3])}."
        elif net_score <= -3:
            decision = "SELL"
            reasoning = f"Strong sell signal. {'. '.join(signals_found[:4])}."
        elif net_score <= -1:
            decision = "SELL"
            reasoning = f"Moderate sell opportunity. {'. '.join(signals_found[:3])}."
        else:
            decision = "HOLD"
            reasoning = "Mixed signals. No clear directional bias."

        return {
            "symbol": symbol,
            "exchange": exchange,
            "decision": decision,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "price": round(latest_close, 2),
            "indicators": {
                "rsi": round(latest_rsi, 2) if latest_rsi else None,
                "ema_9": round(latest_ema_fast, 2) if latest_ema_fast else None,
                "ema_21": round(latest_ema_slow, 2) if latest_ema_slow else None,
                "macd": round(latest_macd, 6) if latest_macd else None,
                "signal": round(latest_signal, 6) if latest_signal else None,
                "bb_upper": round(latest_bb_upper, 2) if latest_bb_upper else None,
                "bb_lower": round(latest_bb_lower, 2) if latest_bb_lower else None,
                "atr": round(latest_atr, 2) if latest_atr else None,
                "volume_ratio": round(self._safe_div(latest_volume, avg_volume), 2) if avg_volume > 0 else None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
