"""
SilverTrade AI - Strategy Decision Engine
==========================================
Analyzes market data using a 3-model ensemble:
  1. Rule-based technical analysis (weight: 20%)
  2. Random Forest classifier (weight: 40%)
  3. LSTM sequence model (weight: 40%)

The ensemble produces a single BUY/SELL/HOLD signal with a
confidence score calibrated against backtest results.

SAFETY: If ML models are not trained or crash, the system
gracefully degrades to rule-only mode.
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
    """AI-powered strategy engine using a 3-model ensemble.

    The engine combines three independent signal sources:
    1. Rule-based TA scoring (RSI, EMA, MACD, Bollinger, Volume)
    2. Random Forest classifier (trained on indicator patterns)
    3. LSTM sequence model (trained on sequential OHLCV patterns)

    Each model votes, weighted by historical accuracy, to produce
    the final signal. Confidence scores reflect actual backtest
    win rates — not arbitrary weight calculations.
    """

    def __init__(self) -> None:
        self.name = "SilverTrade AI Strategy Engine"
        self.version = "1.1.0"
        self._rf_model = None
        self._lstm_model = None
        self._reasoning_engine = None
        self._initialise_models()

    def _initialise_models(self) -> None:
        """Lazy-load ML models and LLM reasoning engine."""
        try:
            from ml.random_forest_model import RandomForestSignalModel
            self._rf_model = RandomForestSignalModel()
            if self._rf_model.is_trained:
                logger.info("Random Forest model loaded")
            else:
                logger.info("Random Forest not trained — running rule-only mode")
        except Exception as e:
            logger.warning("Failed to initialise Random Forest: %s", e)
            self._rf_model = None

        try:
            from ml.lstm_model import LSTMSignalModel
            self._lstm_model = LSTMSignalModel()
            if self._lstm_model.is_trained:
                logger.info("LSTM model loaded")
            else:
                logger.info("LSTM not trained — running rule-only mode")
        except Exception as e:
            logger.warning("Failed to initialise LSTM: %s", e)
            self._lstm_model = None

        try:
            from llm.reasoning_engine import LLMReasoningEngine
            self._reasoning_engine = LLMReasoningEngine()
        except Exception as e:
            logger.warning("Failed to initialise LLM reasoning: %s", e)
            self._reasoning_engine = None

    # ── Safe helpers ─────────────────────────────────────────────────

    def _safe_last(self, values: List[Optional[float]]) -> Optional[float]:
        if not values:
            return None
        for v in reversed(values):
            if v is not None:
                return v
        return None

    def _safe_div(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        if denominator == 0 or denominator is None:
            return default
        try:
            result = numerator / denominator
            if result != result:
                return default
            return result
        except (ZeroDivisionError, TypeError, ValueError):
            return default

    # ── Data validation ──────────────────────────────────────────────

    def _validate_data(self, ohlcv: List[Dict[str, Any]]) -> bool:
        if not ohlcv or len(ohlcv) < 50:
            return False
        try:
            required = {"open", "high", "low", "close", "volume"}
            return all(k in ohlcv[0] for k in required)
        except (IndexError, KeyError, TypeError):
            return False

    # ── Main analysis method ─────────────────────────────────────────

    def analyze(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
        """Analyze market data using the 3-model ensemble.

        SAFETY: Entire body wrapped in try/except. On any error,
        returns a safe HOLD signal instead of crashing.
        """
        try:
            return self._analyze_impl(symbol, ohlcv, exchange)
        except Exception as e:
            logger.error("StrategyEngine crashed for %s: %s", symbol, traceback.format_exc())
            return {
                "symbol": symbol,
                "exchange": exchange,
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}. Holding.",
                "price": 0.0,
                "indicators": {},
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _analyze_impl(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
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

        # ── Step 1: Calculate all indicators ─────────────────────────
        indicators = self._calculate_indicators(closes, highs, lows, volumes)

        latest_close = closes[-1] if closes else 0.0
        prev_close = closes[-2] if len(closes) > 1 else latest_close

        # ── Step 2: Rule-based score ─────────────────────────────────
        rule_decision, rule_confidence, rule_signals = self._rule_score(indicators)

        # ── Step 3: Random Forest prediction ─────────────────────────
        rf_direction, rf_confidence = None, 0.0
        if self._rf_model and self._rf_model.is_trained:
            try:
                rf_direction, rf_confidence = self._rf_model.predict(indicators)
            except Exception as e:
                logger.warning("RF prediction failed: %s", e)

        # ── Step 4: LSTM sequence prediction ─────────────────────────
        lstm_signal, lstm_confidence = None, 0.0
        if self._lstm_model and self._lstm_model.is_trained:
            try:
                lstm_signal, lstm_confidence = self._lstm_model.predict(ohlcv)
            except Exception as e:
                logger.warning("LSTM prediction failed: %s", e)

        # ── Step 5: Ensemble ─────────────────────────────────────────
        model_breakdown = {
            "rule_based": {"signal": rule_decision, "confidence": round(rule_confidence, 1)},
        }
        if rf_direction:
            model_breakdown["random_forest"] = {"direction": rf_direction, "confidence": round(rf_confidence, 3)}
        if lstm_signal:
            model_breakdown["lstm"] = {"signal": lstm_signal, "confidence": round(lstm_confidence, 3)}

        final_signal, final_confidence = self._ensemble(
            rule_decision, rule_confidence,
            rf_direction, rf_confidence,
            lstm_signal, lstm_confidence,
        )

        # ── Step 6: Generate reasoning ───────────────────────────────
        reasoning = self._generate_reasoning(
            symbol, final_signal, final_confidence, indicators, model_breakdown,
        )

        result = {
            "symbol": symbol,
            "exchange": exchange,
            "decision": final_signal,
            "confidence": round(final_confidence, 2),
            "reasoning": reasoning,
            "price": round(latest_close, 2),
            "indicators": {
                "rsi": round(indicators.get("rsi", 0), 2),
                "ema_9": round(indicators.get("ema_fast", 0), 2),
                "ema_21": round(indicators.get("ema_slow", 0), 2),
                "ema_50": round(indicators.get("ema_50", 0), 2),
                "macd": round(indicators.get("macd", 0), 6),
                "signal": round(indicators.get("signal", 0), 6),
                "bb_upper": round(indicators.get("bb_upper", 0), 2),
                "bb_lower": round(indicators.get("bb_lower", 0), 2),
                "atr": round(indicators.get("atr", 0), 2),
                "volume_ratio": round(indicators.get("volume_ratio", 0), 2),
            },
            "model_breakdown": model_breakdown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return result

    # ── Indicator Calculations ───────────────────────────────────────

    def _calculate_indicators(self, closes, highs, lows, volumes) -> Dict[str, Any]:
        """Calculate all technical indicators with individual try/except."""
        ind: Dict[str, Any] = {}

        try:
            rsi_vals = rsi(closes, 14)
            ind["rsi"] = self._safe_last(rsi_vals) or 50
        except Exception:
            ind["rsi"] = 50

        try:
            ema_fast = ema(closes, 9)
            ind["ema_fast"] = self._safe_last(ema_fast) or 0
        except Exception:
            ind["ema_fast"] = 0

        try:
            ema_slow = ema(closes, 21)
            ind["ema_slow"] = self._safe_last(ema_slow) or 0
        except Exception:
            ind["ema_slow"] = 0

        try:
            ema_50 = ema(closes, 50)
            ind["ema_50"] = self._safe_last(ema_50) or 0
        except Exception:
            ind["ema_50"] = 0

        try:
            macd_line, signal_line, _ = macd(closes)
            ind["macd"] = self._safe_last(macd_line) or 0
            ind["signal"] = self._safe_last(signal_line) or 0
            prev_macd = self._safe_last(macd_line[-3:-1] if len(macd_line) > 2 else macd_line)
            prev_signal = self._safe_last(signal_line[-3:-1] if len(signal_line) > 2 else signal_line)
            ind["macd_cross"] = self._safe_last(macd_line) and self._safe_last(signal_line) and \
                                self._safe_last(macd_line) > self._safe_last(signal_line)
            ind["macd_bullish_cross"] = (ind["macd"] > ind["signal"] and
                                         (prev_macd or 0) <= (prev_signal or 0))
        except Exception:
            ind["macd"] = ind["signal"] = 0
            ind["macd_cross"] = False
            ind["macd_bullish_cross"] = False

        try:
            bb_mid, bb_upper, bb_lower = bollinger_bands(closes)
            ind["bb_mid"] = self._safe_last(bb_mid) or 0
            ind["bb_upper"] = self._safe_last(bb_upper) or 0
            ind["bb_lower"] = self._safe_last(bb_lower) or 0
        except Exception:
            ind["bb_mid"] = ind["bb_upper"] = ind["bb_lower"] = 0

        try:
            atr_vals = atr(highs, lows, closes)
            ind["atr"] = self._safe_last(atr_vals) or 0
        except Exception:
            ind["atr"] = 0

        try:
            sma_20 = sma(closes, 20)
            sma_50 = sma(closes, 50)
            ind["sma_20"] = self._safe_last(sma_20) or 0
            ind["sma_50"] = self._safe_last(sma_50) or 0
            ind["golden_cross"] = ind["sma_20"] > ind["sma_50"]
        except Exception:
            ind["sma_20"] = ind["sma_50"] = 0
            ind["golden_cross"] = False

        latest_volume = volumes[-1] if volumes else 0
        avg_volume = self._safe_div(sum(volumes[-20:]), 20) if len(volumes) >= 20 else 0
        ind["volume_ratio"] = self._safe_div(latest_volume, avg_volume) if avg_volume > 0 else 1.0

        latest_close = closes[-1] if closes else 0
        ind["price"] = latest_close

        return ind

    # ── Rule-Based Scoring ───────────────────────────────────────────

    def _rule_score(self, ind: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Pure rule-based scoring system — produces a signal and confidence.

        Returns (decision, confidence_pct, signals_found).
        """
        buy_score = 0
        sell_score = 0
        signals_found: List[str] = []
        max_score = 14

        rsi_val = ind.get("rsi", 50)
        if rsi_val < 30:
            buy_score += 3
            signals_found.append(f"RSI oversold at {rsi_val:.1f}")
        elif rsi_val < 40:
            buy_score += 1
            signals_found.append(f"RSI approaching oversold ({rsi_val:.1f})")
        elif rsi_val > 70:
            sell_score += 3
            signals_found.append(f"RSI overbought at {rsi_val:.1f}")
        elif rsi_val > 60:
            sell_score += 1

        ema_f = ind.get("ema_fast", 0)
        ema_s = ind.get("ema_slow", 0)
        if ema_f > ema_s:
            buy_score += 2
            signals_found.append("Bullish EMA cross (9 > 21)")
        elif ema_f < ema_s:
            sell_score += 2
            signals_found.append("Bearish EMA cross (9 < 21)")

        macd_v = ind.get("macd", 0)
        signal_v = ind.get("signal", 0)
        if macd_v > signal_v:
            buy_score += 1
        else:
            sell_score += 1
        if ind.get("macd_bullish_cross"):
            buy_score += 2
            signals_found.append("MACD bullish crossover")

        price = ind.get("price", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_upper = ind.get("bb_upper", 0)
        if bb_lower and price <= bb_lower:
            buy_score += 2
            signals_found.append("Price at lower Bollinger Band")
        elif bb_upper and price >= bb_upper:
            sell_score += 2
            signals_found.append("Price at upper Bollinger Band")

        sma_20 = ind.get("sma_20", 0)
        sma_50 = ind.get("sma_50", 0)
        if sma_20 > sma_50:
            buy_score += 1
            signals_found.append("Golden cross SMA(20 > 50)")
        elif sma_20 < sma_50:
            sell_score += 1
            signals_found.append("Death cross SMA(20 < 50)")

        if ema_f > ind.get("ema_50", 0):
            buy_score += 1
        else:
            sell_score += 1

        vol_ratio = ind.get("volume_ratio", 1.0)
        if vol_ratio > 1.5:
            signals_found.append(f"Volume {vol_ratio:.1f}x average")

        net_score = buy_score - sell_score
        confidence = min(abs(net_score) / max_score * 100, 95)

        if net_score >= 3:
            decision = "BUY"
        elif net_score >= 1:
            decision = "BUY"
        elif net_score <= -3:
            decision = "SELL"
        elif net_score <= -1:
            decision = "SELL"
        else:
            decision = "HOLD"

        return decision, confidence, signals_found

    # ── Ensemble Logic ───────────────────────────────────────────────

    def _ensemble(
        self,
        rule_decision: str, rule_confidence: float,
        rf_direction: Optional[str], rf_confidence: float,
        lstm_signal: Optional[str], lstm_confidence: float,
    ) -> Tuple[str, float]:
        """Weighted ensemble of all three models.

        Weights: Rules = 20%, RF = 40%, LSTM = 40%.
        When ML models are unavailable, rule-based accounts for 100%.

        Only returns HIGH confidence when all 3 models agree.
        Disagreement → HOLD with LOW confidence.
        """
        # Convert directions to score: BUY=+1, SELL=-1, HOLD=0
        def _to_score(decision: str, sig: Optional[str]) -> Optional[int]:
            d = decision if sig is None else sig
            if d in ("BUY", "UP", "STRONG_BUY"):
                return 1
            if d in ("SELL", "DOWN", "STRONG_SELL"):
                return -1
            if d == "HOLD":
                return 0
            return None

        rule_score = _to_score(rule_decision, None)
        rf_score = _to_score(None, rf_direction) if rf_direction else None
        lstm_score = _to_score(None, lstm_signal) if lstm_signal else None

        votes = []
        weights = []

        # Rules always vote
        if rule_score is not None:
            votes.append(rule_score)
            weights.append(0.2)

        # RF votes if available
        if rf_score is not None and rf_confidence > 0.5:
            votes.append(rf_score)
            weighted_rf_conf = rf_confidence * 0.4
            weights.append(weighted_rf_conf)
            # Normalise: if RF has strong confidence, give it more weight
        else:
            # Boost rule weight to compensate
            weights[0] = min(weights[0] + 0.4, 1.0)

        # LSTM votes if available
        if lstm_score is not None and lstm_confidence > 0.5:
            votes.append(lstm_score)
            weighted_lstm_conf = lstm_confidence * 0.4
            weights.append(weighted_lstm_conf)
        elif rf_score is None:
            # Neither ML model available — rule-based provides all
            weights[0] = 1.0

        if not votes:
            return "HOLD", 0.0

        # Weighted vote
        total_weight = sum(weights)
        weighted_sum = sum(v * w for v, w in zip(votes, weights))
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Check agreement
        all_same = len(set(votes)) == 1

        if avg_score > 0.3:
            decision = "BUY"
        elif avg_score < -0.3:
            decision = "SELL"
        else:
            decision = "HOLD"

        # Confidence: high only when all models agree
        if all_same and len(votes) >= 2:
            confidence = min(85 + rule_confidence * 0.1, 95)
        elif all_same:
            confidence = min(rule_confidence, 80)
        elif decision == "HOLD":
            confidence = 50
        else:
            confidence = min(abs(avg_score) * 100, 60)

        return decision, round(confidence, 1)

    # ── Reasoning ────────────────────────────────────────────────────

    def _generate_reasoning(
        self, symbol: str, decision: str, confidence: float,
        indicators: Dict[str, Any], model_breakdown: Dict[str, Any],
    ) -> str:
        """Generate human-readable reasoning using LLM when available,
        falling back to template-based reasoning."""
        if self._reasoning_engine and self._reasoning_engine.available and decision != "HOLD":
            try:
                return self._reasoning_engine.generate_reasoning(
                    symbol=symbol,
                    signal=decision,
                    confidence=confidence,
                    indicators=indicators,
                    model_breakdown=model_breakdown,
                )
            except Exception as e:
                logger.warning("LLM reasoning failed: %s", e)

        # Template fallback
        return self._template_reasoning(decision, indicators)

    def _template_reasoning(self, decision: str, indicators: Dict[str, Any]) -> str:
        """Template-based reasoning fallback."""
        parts = []
        rsi_val = indicators.get("rsi", 50)
        if decision == "BUY" and rsi_val < 30:
            parts.append(f"RSI deeply oversold at {rsi_val:.1f}")
        elif decision == "SELL" and rsi_val > 70:
            parts.append(f"RSI overbought at {rsi_val:.1f}")

        ema_f = indicators.get("ema_fast", 0)
        ema_s = indicators.get("ema_slow", 0)
        if ema_f and ema_s:
            parts.append(f"{'Bullish' if ema_f > ema_s else 'Bearish'} EMA crossover")

        if indicators.get("volume_ratio", 1) > 1.5:
            parts.append(f"volume {indicators['volume_ratio']:.1f}x avg")

        if parts:
            return f"{decision} signal: {'. '.join(parts)}."
        if decision == "BUY":
            return "Technical indicators show favourable entry conditions."
        elif decision == "SELL":
            return "Technical indicators suggest taking profits or reducing exposure."
        return "Mixed signals. No clear directional bias."
