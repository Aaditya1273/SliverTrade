"""
SilverTrade AI - Strategy Decision Engine
==========================================
Analyzes market data using technical indicators and generates
trading signals with confidence scores and reasoning.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from indicators import atr, bollinger_bands, ema, macd, rsi, sma


class StrategyEngine:
    """AI-powered strategy engine that generates trading signals from market data.

    Uses a combination of technical indicators to evaluate market conditions
    and produce BUY/SELL/HOLD signals with confidence scores and explanations.
    """

    def __init__(self) -> None:
        self.name = "SilverTrade AI Strategy Engine"
        self.version = "1.0.0"

    def _safe_last(self, values: List[Optional[float]]) -> Optional[float]:
        """Get the last non-None value from a list."""
        for v in reversed(values):
            if v is not None:
                return v
        return None

    def _validate_data(self, ohlcv: List[Dict[str, Any]]) -> bool:
        """Validate that we have enough data for indicator calculations."""
        if len(ohlcv) < 50:
            return False
        required = {"open", "high", "low", "close", "volume"}
        return all(k in ohlcv[0] for k in required)

    def analyze(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
        """Analyze market data and return a trading signal.

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            ohlcv: List of OHLCV candles (most recent first or last)
            exchange: Exchange name

        Returns:
            Signal dict with decision, confidence, reasoning, or None if data insufficient
        """
        if not self._validate_data(ohlcv):
            return None

        # Ensure data is sorted oldest → newest
        if ohlcv[0].get("time", 0) > ohlcv[-1].get("time", 0):
            ohlcv = list(reversed(ohlcv))

        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        opens = [c["open"] for c in ohlcv]
        volumes = [c.get("volume", 0) for c in ohlcv]

        # ── Calculate Indicators ──────────────────────────────────────
        rsi_vals = rsi(closes, 14)
        ema_fast = ema(closes, 9)
        ema_slow = ema(closes, 21)
        ema_50 = ema(closes, 50)
        macd_line, signal_line, histogram = macd(closes)
        bb_mid, bb_upper, bb_lower = bollinger_bands(closes)
        atr_vals = atr(highs, lows, closes)
        sma_20 = sma(closes, 20)
        sma_50 = sma(closes, 50)

        # ── Extract Latest Values ─────────────────────────────────────
        latest_close = closes[-1]
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
        latest_bb_mid = self._safe_last(bb_mid)
        latest_atr = self._safe_last(atr_vals)
        latest_sma_20 = self._safe_last(sma_20)
        latest_sma_50 = self._safe_last(sma_50)
        latest_volume = volumes[-1]
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        prev_close = closes[-2] if len(closes) > 1 else latest_close

        # ── Scoring System ────────────────────────────────────────────
        buy_score = 0
        sell_score = 0
        signals_found: List[str] = []
        # Maximum possible score: each of the 7 indicator groups contributes up to N points
        # 1. RSI: ±3, 2. EMA cross: ±2, 3. MACD: ±3 (1 + 2), 4. Bollinger: ±2,
        # 5. Trend (SMA): ±2 (1+1), 6. Volume: ±1, 7. EMA 50: ±1  Total: 14
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
                # MACD crossover detection
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
        confidence_base = min(abs(net_score) / max_score * 100, 95)
        volatility_factor = min((latest_atr / latest_close * 100) if latest_atr and latest_close else 0, 5)
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
                "volume_ratio": round(latest_volume / avg_volume, 2) if avg_volume > 0 else None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
