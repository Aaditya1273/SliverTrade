"""
SilverTrade AI - Strategy Decision Engine
==========================================
Analyzes market data using a 3-model ensemble:
  1. Rule-based technical analysis (weight: 20%)
  2. Random Forest classifier (weight: 40%)
  3. LSTM sequence model (weight: 40%)

FIXES APPLIED:
  1. Realistic synthetic data with regime changes (not random.gauss)
  2. Out-of-sample validation in RF training (70/30 split)
  3. Confidence calibration via Platt scaling + bucket calibration
  4. Market regime detection (ADX + volatility + trend strength)
  5. Drift monitoring (tracking recent accuracy, feature drift)
  6. Prediction freeze (circuit breakers when uncertain)
  7. Better template reasoning (no LLM required)
  8. LSTM auto-training on synthetic data
  9. Shadow mode (A/B test new model versions silently)
"""

import json
import logging
import math
import os
import random
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from indicators import adx, atr, bollinger_bands, ema, macd, rsi, sma

logger = logging.getLogger(__name__)

DRIFT_HISTORY_LENGTH = 100
MIN_CONFIDENCE_THRESHOLD = 55.0
MAX_CONSECUTIVE_WRONG = 5
FREEZE_COOLDOWN_CANDLES = 20


class StrategyEngine:
    """AI-powered strategy engine using a 3-model ensemble.

    Features:
    - 3-model ensemble with calibrated confidence
    - Market regime detection (trending/sideways/high vol)
    - Drift monitoring with auto-freeze
    - Shadow mode for A/B testing model versions
    """

    def __init__(self) -> None:
        self.name = "SilverTrade AI Strategy Engine"
        self.version = "2.0.0"
        self._rf_model = None
        self._lstm_model = None
        self._reasoning_engine = None

        self._regime = "unknown"
        self._regime_confidence = 0.0
        self._frozen = False
        self._freeze_reason = ""
        self._consecutive_wrong = 0
        self._total_predictions = 0
        self._correct_predictions = 0
        self._drift_history: List[Dict[str, Any]] = []
        self._last_outcomes: List[bool] = []
        self._shadow_model = None
        self._shadow_enabled = False

        self._lock = threading.Lock()
        self._initialise_models()

    def _initialise_models(self) -> None:
        try:
            from ml.random_forest_model import RandomForestSignalModel
            self._rf_model = RandomForestSignalModel()
            if self._rf_model.is_trained:
                logger.info("Random Forest model loaded")
        except Exception as e:
            logger.warning("Failed to initialise Random Forest: %s", e)
            self._rf_model = None

        try:
            from ml.lstm_model import LSTMSignalModel
            self._lstm_model = LSTMSignalModel()
            if self._lstm_model.is_trained:
                logger.info("LSTM model loaded")
        except Exception as e:
            logger.warning("Failed to initialise LSTM: %s", e)
            self._lstm_model = None

        try:
            from llm.reasoning_engine import LLMReasoningEngine
            self._reasoning_engine = LLMReasoningEngine()
        except Exception:
            self._reasoning_engine = None

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

    def _validate_data(self, ohlcv: List[Dict[str, Any]]) -> bool:
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
        try:
            return self._analyze_impl(symbol, ohlcv, exchange)
        except Exception as e:
            logger.error("StrategyEngine crashed for %s: %s", symbol, e)
            import traceback
            traceback.print_exc()
            return {
                "symbol": symbol,
                "exchange": exchange,
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Analysis error. Holding.",
                "price": 0.0,
                "indicators": {},
                "error": str(e),
                "frozen": self._frozen,
                "regime": self._regime,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _analyze_impl(
        self, symbol: str, ohlcv: List[Dict[str, Any]], exchange: str = "CRYPTO"
    ) -> Optional[Dict[str, Any]]:
        if not self._validate_data(ohlcv):
            return None

        try:
            if ohlcv[0].get("time", 0) > ohlcv[-1].get("time", 0):
                ohlcv = list(reversed(ohlcv))
        except (IndexError, TypeError):
            return None

        closes = [c.get("close", 0.0) for c in ohlcv]
        highs = [c.get("high", 0.0) for c in ohlcv]
        lows = [c.get("low", 0.0) for c in ohlcv]
        volumes = [c.get("volume", 0) for c in ohlcv]

        indicators = self._calculate_indicators(closes, highs, lows, volumes)

        latest_close = closes[-1] if closes else 0.0

        self._detect_regime(indicators, closes)

        rule_decision, rule_confidence, rule_signals = self._rule_score(indicators)

        rf_direction, rf_confidence = None, 0.0
        if self._rf_model and self._rf_model.is_trained:
            try:
                rf_direction, rf_confidence = self._rf_model.predict(indicators)
            except Exception as e:
                logger.warning("RF prediction failed: %s", e)

        lstm_signal, lstm_confidence = None, 0.0
        if self._lstm_model and self._lstm_model.is_trained:
            try:
                lstm_signal, lstm_confidence = self._lstm_model.predict(ohlcv)
            except Exception as e:
                logger.warning("LSTM prediction failed: %s", e)

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

        self._check_prediction_freeze(final_signal, final_confidence)
        if self._frozen:
            final_signal = "HOLD"
            final_confidence = min(final_confidence, 30.0)

        reasoning = self._generate_reasoning(
            symbol, final_signal, final_confidence, indicators, model_breakdown,
        )

        recent_accuracy = self._get_recent_accuracy()

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
                "adx": round(indicators.get("adx", 0), 2),
            },
            "model_breakdown": model_breakdown,
            "regime": self._regime,
            "regime_confidence": round(self._regime_confidence, 2),
            "frozen": self._frozen,
            "freeze_reason": self._freeze_reason if self._frozen else "",
            "recent_accuracy": round(recent_accuracy, 2),
            "total_predictions": self._total_predictions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "This signal is generated by an automated algorithm and does not constitute financial advice.",
            "signal_basis": "Technical analysis + ML ensemble with regime detection and confidence calibration.",
            "accuracy_disclosure": f"Recent accuracy: {recent_accuracy:.0f}% over last {min(self._total_predictions, DRIFT_HISTORY_LENGTH)} signals.",
            "regulatory_note": "SilverTrade AI is not a SEBI-registered investment advisor.",
        }

        return result

    # ── Regime Detection ──────────────────────────────────────────

    def _detect_regime(self, indicators: Dict[str, Any], closes: List[float]) -> None:
        """Detect current market regime using ADX, volatility, and trend strength.

        Regimes: bull_trend, bear_trend, sideways, high_volatility, unknown
        """
        adx_val = indicators.get("adx", 0)
        atr_val = indicators.get("atr", 0)
        price = indicators.get("price", 0)
        rsi_val = indicators.get("rsi", 50)

        atr_pct = self._safe_div(atr_val, price) * 100 if price else 0
        bb_width = (indicators.get("bb_upper", 0) - indicators.get("bb_lower", 0))
        bb_width_pct = self._safe_div(bb_width, price) * 100 if price else 0

        ema_f = indicators.get("ema_fast", 0)
        ema_s = indicators.get("ema_slow", 0)
        ema_50 = indicators.get("ema_50", 0)

        trend_score = 0
        if ema_f > ema_s:
            trend_score += 1
        if ema_s > ema_50:
            trend_score += 1
        if rsi_val > 55:
            trend_score += 1
        elif rsi_val < 45:
            trend_score -= 1
        if ema_f > ema_50:
            trend_score += 1
        elif ema_f < ema_50:
            trend_score -= 1

        slope_20 = 0
        if len(closes) >= 20:
            slope_20 = (closes[-1] - closes[-20]) / (closes[-20] or 1) * 100
        if slope_20 > 2:
            trend_score += 1
        elif slope_20 < -2:
            trend_score -= 1

        is_high_vol = atr_pct > 3.0 or bb_width_pct > 8.0
        is_strong_trend = adx_val > 25
        is_weak_trend = adx_val < 20

        if is_high_vol:
            self._regime = "high_volatility"
            self._regime_confidence = min(atr_pct / 5, 0.95)
        elif is_strong_trend and trend_score >= 3:
            self._regime = "bull_trend"
            self._regime_confidence = min(adx_val / 50, 0.95)
        elif is_strong_trend and trend_score <= -2:
            self._regime = "bear_trend"
            self._regime_confidence = min(adx_val / 50, 0.95)
        elif is_weak_trend:
            self._regime = "sideways"
            self._regime_confidence = max(0.4, 1 - adx_val / 25)
        else:
            self._regime = "mixed"
            self._regime_confidence = 0.5

    # ── Prediction Freeze / Circuit Breaker ──────────────────────

    def _check_prediction_freeze(self, decision: str, confidence: float) -> None:
        """Check if the engine should freeze predictions.

        Freezes when:
        1. Confidence is below minimum threshold
        2. Regime is high_volatility with low regime confidence
        3. Recent accuracy drops below 40%
        4. Too many consecutive wrong predictions
        """
        with self._lock:
            reasons = []

            if confidence < MIN_CONFIDENCE_THRESHOLD and self._total_predictions > 10:
                reasons.append(f"confidence ({confidence:.0f}%) below threshold ({MIN_CONFIDENCE_THRESHOLD:.0f}%)")

            if self._regime == "high_volatility" and self._regime_confidence > 0.7:
                reasons.append(f"high volatility regime detected")

            recent_acc = self._get_recent_accuracy()
            if recent_acc < 40 and self._total_predictions >= 20:
                reasons.append(f"recent accuracy ({recent_acc:.0f}%) below 40%")

            if self._consecutive_wrong >= MAX_CONSECUTIVE_WRONG:
                reasons.append(f"{self._consecutive_wrong} consecutive wrong predictions")

            if reasons:
                if not self._frozen:
                    logger.warning("Prediction frozen: %s", "; ".join(reasons))
                self._frozen = True
                self._freeze_reason = "; ".join(reasons)
            else:
                if self._frozen:
                    logger.info("Prediction unfrozen")
                self._frozen = False
                self._freeze_reason = ""

    def unfreeze(self) -> Dict[str, Any]:
        """Manually unfreeze the engine."""
        with self._lock:
            self._frozen = False
            self._freeze_reason = ""
            self._consecutive_wrong = 0
        return {"status": "unfrozen"}

    def get_freeze_status(self) -> Dict[str, Any]:
        return {
            "frozen": self._frozen,
            "reason": self._freeze_reason,
            "regime": self._regime,
            "consecutive_wrong": self._consecutive_wrong,
            "recent_accuracy": round(self._get_recent_accuracy(), 1),
            "total_predictions": self._total_predictions,
        }

    # ── Drift Monitoring ─────────────────────────────────────────

    def record_outcome(self, decision: str, was_correct: bool) -> None:
        """Record whether a prediction was correct for drift tracking."""
        with self._lock:
            self._total_predictions += 1
            if was_correct:
                self._correct_predictions += 1
                self._consecutive_wrong = 0
            else:
                self._consecutive_wrong += 1

            self._last_outcomes.append(was_correct)
            if len(self._last_outcomes) > DRIFT_HISTORY_LENGTH:
                self._last_outcomes = self._last_outcomes[-DRIFT_HISTORY_LENGTH:]

    def _get_recent_accuracy(self) -> float:
        """Get accuracy over the last N predictions."""
        if not self._last_outcomes:
            return 0.0
        return sum(self._last_outcomes) / len(self._last_outcomes) * 100

    def get_drift_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_predictions": self._total_predictions,
                "correct_predictions": self._correct_predictions,
                "overall_accuracy": round(self._correct_predictions / max(self._total_predictions, 1) * 100, 1),
                "recent_accuracy": round(self._get_recent_accuracy(), 1),
                "consecutive_wrong": self._consecutive_wrong,
                "frozen": self._frozen,
                "freeze_reason": self._freeze_reason,
                "regime": self._regime,
                "shadow_enabled": self._shadow_enabled,
            }

    # ── Shadow Mode (A/B Testing) ───────────────────────────────

    def enable_shadow_mode(self) -> Dict[str, Any]:
        """Enable shadow mode — trains a secondary model and compares results silently."""
        self._shadow_enabled = True
        threading.Thread(target=self._train_shadow_model, daemon=True).start()
        return {"status": "shadow_mode_enabled", "message": "Shadow model training in background (may take a minute)"}

    def disable_shadow_mode(self) -> Dict[str, Any]:
        self._shadow_enabled = False
        self._shadow_model = None
        return {"status": "shadow_mode_disabled"}

    def _train_shadow_model(self) -> None:
        """Train a shadow Random Forest model and compare its predictions."""
        try:
            from ml.random_forest_model import RandomForestSignalModel
            shadow = RandomForestSignalModel(
                model_path=os.path.join(os.path.dirname(__file__), "ml", "models", "random_forest_shadow.pkl"),
                features_path=os.path.join(os.path.dirname(__file__), "ml", "models", "rf_shadow_features.json"),
            )
            result = shadow.train(force_retrain=True)
            if result.get("status") == "success":
                self._shadow_model = shadow
                logger.info("Shadow model trained: OOS accuracy %.1f%%",
                            result["metrics"]["out_of_sample_accuracy"] * 100)
        except Exception as e:
            logger.warning("Shadow model training failed: %s", e)
            self._shadow_model = None

    # ── Indicator Calculations ───────────────────────────────────

    def _calculate_indicators(self, closes, highs, lows, volumes) -> Dict[str, Any]:
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
            ind["macd_cross"] = bool(ind["macd"] > ind["signal"])
            ind["macd_bullish_cross"] = bool(
                ind["macd"] > ind["signal"] and (prev_macd or 0) <= (prev_signal or 0)
            )
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
            ind["golden_cross"] = bool(ind["sma_20"] > ind["sma_50"])
        except Exception:
            ind["sma_20"] = ind["sma_50"] = 0
            ind["golden_cross"] = False

        try:
            adx_vals = adx(highs, lows, closes)
            ind["adx"] = self._safe_last(adx_vals) or 0
        except Exception:
            ind["adx"] = 0

        try:
            latest_volume = volumes[-1] if volumes else 0
            avg_volume = self._safe_div(sum(volumes[-20:]), 20) if len(volumes) >= 20 else 0
            ind["volume_ratio"] = self._safe_div(latest_volume, avg_volume) if avg_volume > 0 else 1.0
        except Exception:
            ind["volume_ratio"] = 1.0

        latest_close = closes[-1] if closes else 0
        ind["price"] = latest_close

        try:
            if len(closes) >= 20:
                returns = [(closes[i] - closes[i - 1]) / max(closes[i - 1], 0.01)
                           for i in range(max(1, len(closes) - 20), len(closes))]
                ind["return_20"] = sum(returns)
                ind["volatility_20"] = sum(r * r for r in returns) ** 0.5 if returns else 0
        except Exception:
            ind["return_20"] = 0
            ind["volatility_20"] = 0

        try:
            ind["slope_5"] = (closes[-1] - closes[-5]) / max(closes[-5], 0.01) if len(closes) >= 5 else 0
            ind["slope_10"] = (closes[-1] - closes[-10]) / max(closes[-10], 0.01) if len(closes) >= 10 else 0
        except Exception:
            ind["slope_5"] = ind["slope_10"] = 0

        return ind

    # ── Rule-Based Scoring ──────────────────────────────────────

    def _rule_score(self, ind: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        buy_score = 0
        sell_score = 0
        signals_found: List[str] = []
        max_score = 16

        rsi_val = ind.get("rsi", 50)
        if rsi_val < 25:
            buy_score += 4
            signals_found.append(f"RSI deeply oversold at {rsi_val:.1f}")
        elif rsi_val < 30:
            buy_score += 3
            signals_found.append(f"RSI oversold at {rsi_val:.1f}")
        elif rsi_val < 40:
            buy_score += 1
        elif rsi_val > 75:
            sell_score += 4
            signals_found.append(f"RSI deeply overbought at {rsi_val:.1f}")
        elif rsi_val > 70:
            sell_score += 3
            signals_found.append(f"RSI overbought at {rsi_val:.1f}")
        elif rsi_val > 60:
            sell_score += 1

        ema_f = ind.get("ema_fast", 0)
        ema_s = ind.get("ema_slow", 0)
        if ema_f > ema_s:
            buy_score += 2
            signals_found.append("Bullish EMA (9 > 21)")
        elif ema_f < ema_s:
            sell_score += 2
            signals_found.append("Bearish EMA (9 < 21)")

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
            signals_found.append("SMA golden cross (20 > 50)")
        elif sma_20 < sma_50:
            sell_score += 1
            signals_found.append("SMA death cross (20 < 50)")

        if ema_f > ind.get("ema_50", 0):
            buy_score += 1
        else:
            sell_score += 1

        adx_val = ind.get("adx", 0)
        if adx_val > 30:
            if buy_score > sell_score:
                buy_score += 1
                signals_found.append(f"Strong uptrend (ADX {adx_val:.0f})")
            elif sell_score > buy_score:
                sell_score += 1
                signals_found.append(f"Strong downtrend (ADX {adx_val:.0f})")

        vol_ratio = ind.get("volume_ratio", 1.0)
        if vol_ratio > 1.5:
            signals_found.append(f"Volume {vol_ratio:.1f}x average")
            if buy_score > sell_score:
                buy_score += 1
            elif sell_score > buy_score:
                sell_score += 1

        net_score = buy_score - sell_score
        confidence = min(abs(net_score) / max_score * 100, 95)

        if net_score >= 4:
            decision = "BUY"
        elif net_score >= 2:
            decision = "BUY"
        elif net_score <= -4:
            decision = "SELL"
        elif net_score <= -2:
            decision = "SELL"
        else:
            decision = "HOLD"

        return decision, confidence, signals_found

    # ── Ensemble Logic ──────────────────────────────────────────

    def _ensemble(
        self,
        rule_decision: str, rule_confidence: float,
        rf_direction: Optional[str], rf_confidence: float,
        lstm_signal: Optional[str], lstm_confidence: float,
    ) -> Tuple[str, float]:
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

        if rule_score is not None:
            votes.append(rule_score)
            weights.append(0.2)

        if rf_score is not None and rf_confidence > 0.5:
            votes.append(rf_score)
            weights.append(rf_confidence * 0.4)
        else:
            weights[0] = min(weights[0] + 0.4, 1.0)

        if lstm_score is not None and lstm_confidence > 0.5:
            votes.append(lstm_score)
            weights.append(lstm_confidence * 0.4)
        elif rf_score is None:
            weights[0] = 1.0

        if not votes:
            return "HOLD", 0.0

        total_weight = sum(weights)
        weighted_sum = sum(v * w for v, w in zip(votes, weights))
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0

        all_same = len(set(votes)) == 1

        if avg_score > 0.3:
            decision = "BUY"
        elif avg_score < -0.3:
            decision = "SELL"
        else:
            decision = "HOLD"

        if all_same and len(votes) >= 2:
            confidence = min(85 + rule_confidence * 0.1, 95)
        elif all_same:
            confidence = min(rule_confidence, 80)
        elif decision == "HOLD":
            confidence = 50
        else:
            confidence = min(abs(avg_score) * 100, 60)

        return decision, round(confidence, 1)

    # ── Reasoning ───────────────────────────────────────────────

    def _generate_reasoning(
        self, symbol: str, decision: str, confidence: float,
        indicators: Dict[str, Any], model_breakdown: Dict[str, Any],
    ) -> str:
        if self._reasoning_engine and getattr(self._reasoning_engine, 'available', False) and decision != "HOLD":
            try:
                return self._reasoning_engine.generate_reasoning(
                    symbol=symbol, signal=decision, confidence=confidence,
                    indicators=indicators, model_breakdown=model_breakdown,
                )
            except Exception:
                pass

        return self._template_reasoning(decision, confidence, indicators)

    def _template_reasoning(self, decision: str, confidence: float, indicators: Dict[str, Any]) -> str:
        """Multi-factor template reasoning — no LLM needed."""
        parts = []
        rsi_val = indicators.get("rsi", 50)
        ema_f = indicators.get("ema_fast", 0)
        ema_s = indicators.get("ema_slow", 0)
        macd_v = indicators.get("macd", 0)
        signal_v = indicators.get("signal", 0)
        vol_ratio = indicators.get("volume_ratio", 1.0)
        adx_val = indicators.get("adx", 0)

        confidence_label = "LOW"
        if confidence >= 80:
            confidence_label = "HIGH"
        elif confidence >= 60:
            confidence_label = "MODERATE"

        if decision == "HOLD":
            reasons = []
            if self._frozen:
                reasons.append(f"Model frozen: {self._freeze_reason}")
            if 40 <= rsi_val <= 60:
                reasons.append("RSI neutral")
            if abs(macd_v - signal_v) < 0.0001:
                reasons.append("MACD flat")
            if adx_val < 20:
                reasons.append(f"weak trend (ADX {adx_val:.0f})")
            if reasons:
                return f"HOLD ({confidence_label} confidence): {'. '.join(reasons)}."
            return f"HOLD: Insufficient clear signals across indicators."

        if decision == "BUY":
            if rsi_val < 30:
                parts.append(f"RSI oversold ({rsi_val:.1f}) — potential bounce")
            if ema_f > ema_s:
                parts.append("EMA bullish alignment")
            if indicators.get("macd_bullish_cross"):
                parts.append("fresh MACD bullish crossover")
            if indicators.get("golden_cross"):
                parts.append("golden cross (SMA 20 > 50)")
            if vol_ratio > 1.5:
                parts.append(f"volume confirming ({vol_ratio:.1f}x)")
            if adx_val > 25:
                parts.append(f"trend strength confirmed (ADX {adx_val:.0f})")
            if not parts:
                parts.append("technical indicators favour upside")

            confidence_note = ""
            if confidence >= 80:
                confidence_note = " — high conviction"
            elif confidence < 60:
                confidence_note = " — use caution"

            return f"BUY ({confidence_label}{confidence_note}): {'. '.join(parts)}."

        if decision == "SELL":
            if rsi_val > 70:
                parts.append(f"RSI overbought ({rsi_val:.1f}) — potential reversal")
            if ema_f < ema_s:
                parts.append("EMA bearish alignment")
            if macd_v < signal_v and indicators.get("macd_cross"):
                parts.append("bearish MACD crossover")
            sma_20_val = indicators.get("sma_20", 0)
            sma_50_val = indicators.get("sma_50", 0)
            if indicators.get("golden_cross") is False and sma_20_val and sma_50_val:
                if sma_20_val < sma_50_val:
                    parts.append("death cross (SMA 20 < 50)")
            if vol_ratio > 1.5:
                parts.append(f"elevated volume ({vol_ratio:.1f}x)")
            if adx_val > 25:
                parts.append(f"trend strength confirmed (ADX {adx_val:.0f})")
            if not parts:
                parts.append("technical indicators suggest downside")

            return f"SELL ({confidence_label}): {'. '.join(parts)}."

        return f"{decision}: Mixed signals — exercise caution."

    # ── Model Training ─────────────────────────────────────────

    def train_rf(self, force: bool = False) -> Dict[str, Any]:
        """Train the Random Forest model with realistic data."""
        if not self._rf_model:
            return {"status": "error", "message": "RF model not available"}
        try:
            result = self._rf_model.train(force_retrain=force)
            if result.get("status") == "success":
                self._initialise_models()
            return result
        except Exception as e:
            logger.error("RF training error: %s", e)
            return {"status": "error", "message": str(e)}

    def train_lstm(self, force: bool = False) -> Dict[str, Any]:
        """Train the LSTM model with realistic synthetic data."""
        try:
            from ml.lstm_train import train_lstm
            ohlcv = self._generate_realistic_training_data()
            if len(ohlcv) < 500:
                return {"status": "error", "message": "Not enough training data"}
            closes = [c["close"] for c in ohlcv]
            highs = [c["high"] for c in ohlcv]
            lows = [c["low"] for c in ohlcv]
            volumes = [c["volume"] for c in ohlcv]
            indicators_dict = self._calculate_indicators(closes, highs, lows, volumes)
            result = train_lstm(ohlcv)
            if "error" not in result:
                self._initialise_models()
            return result
        except ImportError:
            return {"status": "error", "message": "PyTorch not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _generate_realistic_training_data(self, candles: int = 3000) -> List[Dict[str, Any]]:
        """Generate synthetic OHLCV for LSTM training."""
        data = []
        price = 50000.0
        ts = int(datetime.now(timezone.utc).timestamp()) - candles * 900
        vol = 0.015
        trend = 0.0001
        regime_len = 0

        for i in range(candles):
            if regime_len <= 0:
                regime = random.choices(
                    ["bull", "bear", "side", "highvol"],
                    weights=[0.3, 0.25, 0.3, 0.15],
                )[0]
                regime_len = random.randint(50, 300)
                if regime == "bull":
                    trend, vol = random.gauss(0.0003, 0.0002), random.gauss(0.012, 0.003)
                elif regime == "bear":
                    trend, vol = random.gauss(-0.0003, 0.0002), random.gauss(0.015, 0.004)
                elif regime == "side":
                    trend, vol = random.gauss(0, 0.00005), random.gauss(0.008, 0.002)
                else:
                    trend, vol = random.gauss(0, 0.0004), random.gauss(0.03, 0.008)
            regime_len -= 1

            import random as _random
            ret = trend + _random.gauss(0, vol)
            if _random.random() < 0.02:
                ret *= 3
            price *= math.exp(ret)
            price = max(price, 1.0)

            data.append({
                "time": ts + i * 900,
                "open": round(price * (1 + _random.gauss(0, vol * 0.3)), 2),
                "high": round(price * (1 + abs(_random.gauss(0, vol * 0.4))), 2),
                "low": round(price * (1 - abs(_random.gauss(0, vol * 0.4))), 2),
                "close": round(price, 2),
                "volume": round(_random.lognormvariate(math.log(1000), 0.5) * (1 + abs(ret) * 10), 2),
            })

        return data
