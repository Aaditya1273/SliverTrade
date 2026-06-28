"""
Unit Tests: StrategyEngine Ensemble Logic
==========================================
Tests the 3-model ensemble (Rules 20%, RF 40%, LSTM 40%) with
all combinations of model availability, agreement, and edge cases.
"""

import sys
sys.path.insert(0, ".")

import pytest
from strategy_engine import StrategyEngine


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """Fresh engine with no trained ML models (they fail silently)."""
    e = StrategyEngine()
    # Force ML models to None for isolated rule testing
    e._rf_model = None
    e._lstm_model = None
    return e


@pytest.fixture
def ohlcv():
    """Generate 60 candle OHLCV with a clear uptrend for testing."""
    candles = []
    price = 50000
    for i in range(60):
        price += 50 + (i % 5) * 10  # uptrend with some noise
        candles.append({
            "time": 1700000000 + i * 900,
            "open": round(price - 20, 2),
            "high": round(price + 30, 2),
            "low": round(price - 40, 2),
            "close": round(price, 2),
            "volume": round(1000 + i * 10, 2),
        })
    return candles


# ── Safe Helpers ─────────────────────────────────────────────────────

class TestSafeHelpers:
    def test_safe_last_returns_last_non_none(self, engine):
        assert engine._safe_last([1, 2, 3]) == 3
        assert engine._safe_last([None, 2, None]) == 2
        assert engine._safe_last([None, None, 5]) == 5

    def test_safe_last_empty_or_all_none(self, engine):
        assert engine._safe_last([]) is None
        assert engine._safe_last([None, None]) is None

    def test_safe_div_normal(self, engine):
        assert engine._safe_div(10, 5) == 2.0
        assert engine._safe_div(-10, 5) == -2.0
        assert engine._safe_div(0, 5) == 0.0

    def test_safe_div_by_zero(self, engine):
        assert engine._safe_div(10, 0) == 0.0
        assert engine._safe_div(10, 0, default=-1) == -1

    def test_safe_div_none(self, engine):
        assert engine._safe_div(10, None) == 0.0
        assert engine._safe_div(10, None, default=42) == 42

    def test_safe_div_nan(self, engine):
        assert engine._safe_div(float("nan"), 5, default=0) == 0.0


# ── Data Validation ──────────────────────────────────────────────────

class TestValidateData:
    def test_valid_data_returns_true(self, engine, ohlcv):
        assert engine._validate_data(ohlcv) is True

    def test_empty_data_returns_false(self, engine):
        assert engine._validate_data([]) is False

    def test_none_data_returns_false(self, engine):
        assert engine._validate_data(None) is False

    def test_too_few_candles_returns_false(self, engine):
        assert engine._validate_data([{"open": 1, "high": 2, "low": 1, "close": 2, "volume": 100}]) is False

    def test_missing_keys_returns_false(self, engine):
        bad = [{"open": 1, "high": 2}] * 50  # missing close, volume
        assert engine._validate_data(bad) is False


# ── Rule-Based Scoring ───────────────────────────────────────────────

class TestRuleScore:
    def test_rsi_oversold_gives_buy(self, engine):
        """RSI < 30 should produce a BUY signal."""
        ind = {
            "rsi": 25, "ema_fast": 100, "ema_slow": 90, "ema_50": 85,
            "macd": 5, "signal": 3, "macd_bullish_cross": True,
            "price": 100, "bb_lower": 95, "bb_upper": 110,
            "sma_20": 98, "sma_50": 92,
            "volume_ratio": 1.2, "atr": 5,
        }
        decision, confidence, signals = engine._rule_score(ind)
        assert decision == "BUY", f"Expected BUY, got {decision}"
        assert confidence > 0, f"Expected positive confidence, got {confidence}"
        assert any("RSI oversold" in s for s in signals), f"Expected RSI oversold signal, got {signals}"

    def test_rsi_overbought_gives_sell(self, engine):
        """RSI > 70 should produce a SELL signal."""
        ind = {
            "rsi": 75, "ema_fast": 100, "ema_slow": 110, "ema_50": 115,
            "macd": 3, "signal": 5, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 85, "bb_upper": 105,
            "sma_20": 98, "sma_50": 105,
            "volume_ratio": 0.8, "atr": 5,
        }
        decision, confidence, signals = engine._rule_score(ind)
        assert decision == "SELL", f"Expected SELL, got {decision}"
        assert confidence > 0
        assert any("RSI overbought" in s for s in signals)

    def test_neutral_indicators_give_hold(self, engine):
        """Balanced buy/sell signals should produce HOLD."""
        # buy: ema_fast > ema_slow (+2), sell: macd < signal (+1), ema_fast < ema_50 (+1) → net=0
        ind = {
            "rsi": 50,
            "ema_fast": 105, "ema_slow": 100, "ema_50": 106,
            "macd": -1, "signal": 0, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 100, "sma_50": 100,
            "volume_ratio": 1.0, "atr": 5,
        }
        decision, confidence, signals = engine._rule_score(ind)
        assert decision == "HOLD", f"Expected HOLD, got {decision}"

    def test_price_at_lower_band_adds_buy_signals(self, engine):
        """Price at lower Bollinger Band should add a buy signal."""
        ind = {
            "rsi": 45, "ema_fast": 100, "ema_slow": 99, "ema_50": 95,
            "macd": 1, "signal": 0, "macd_bullish_cross": False,
            "price": 90, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 98, "sma_50": 96,
            "volume_ratio": 1.0, "atr": 5,
        }
        decision, confidence, signals = engine._rule_score(ind)
        assert decision == "BUY"
        assert any("lower Bollinger" in s for s in signals)

    def test_price_at_upper_band_adds_sell_signals(self, engine):
        """Price at upper Bollinger Band with bearish indicators = SELL."""
        # All indicators bearish: RSI>60 (+1 sell), EMA bearish (+2 sell),
        # MACD bearish (+1 sell), upper BB (+2 sell), death cross (+1 sell)
        # Total sell=8, buy=0 → net=-8 → SELL
        ind = {
            "rsi": 65, "ema_fast": 100, "ema_slow": 110, "ema_50": 115,
            "macd": 2, "signal": 3, "macd_bullish_cross": False,
            "price": 110, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 100, "sma_50": 105,
            "volume_ratio": 1.0, "atr": 5,
        }
        decision, confidence, signals = engine._rule_score(ind)
        assert decision == "SELL", f"Expected SELL, got {decision}"
        assert any("upper Bollinger" in s for s in signals)

    def test_golden_cross_adds_signal(self, engine):
        """SMA 20 > SMA 50 should add golden cross signal."""
        ind = {
            "rsi": 50, "ema_fast": 100, "ema_slow": 99, "ema_50": 95,
            "macd": 0, "signal": 0, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 105, "sma_50": 100,
            "volume_ratio": 1.0, "atr": 5,
        }
        d, c, signals = engine._rule_score(ind)
        assert any("golden cross" in s for s in signals)

    def test_death_cross_adds_signal(self, engine):
        """SMA 20 < SMA 50 should add death cross signal."""
        ind = {
            "rsi": 50, "ema_fast": 100, "ema_slow": 101, "ema_50": 105,
            "macd": 0, "signal": 0, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 100, "sma_50": 105,
            "volume_ratio": 1.0, "atr": 5,
        }
        d, c, signals = engine._rule_score(ind)
        assert any("death cross" in s for s in signals)

    def test_high_volume_adds_signal(self, engine):
        """Volume > 1.5x average should add a volume signal."""
        ind = {
            "rsi": 50, "ema_fast": 100, "ema_slow": 101, "ema_50": 100,
            "macd": 0, "signal": 0, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 90, "bb_upper": 110,
            "sma_20": 100, "sma_50": 100,
            "volume_ratio": 2.0, "atr": 5,
        }
        d, c, signals = engine._rule_score(ind)
        assert any("Volume" in s and "2.0x" in s for s in signals)

    def test_higher_confidence_with_stronger_signals(self, engine):
        """Stronger agreement should produce higher confidence."""
        ind_weak = {
            "rsi": 45, "ema_fast": 100, "ema_slow": 99, "ema_50": 98,
            "macd": 0, "signal": 0, "macd_bullish_cross": False,
            "price": 100, "bb_lower": 95, "bb_upper": 105,
            "sma_20": 100, "sma_50": 99,
            "volume_ratio": 1.0, "atr": 5,
        }
        ind_strong = {
            "rsi": 25, "ema_fast": 100, "ema_slow": 50, "ema_50": 40,
            "macd": 10, "signal": 3, "macd_bullish_cross": True,
            "price": 100, "bb_lower": 100, "bb_upper": 150,
            "sma_20": 90, "sma_50": 60,
            "volume_ratio": 2.0, "atr": 5,
        }
        _, weak_conf, _ = engine._rule_score(ind_weak)
        _, strong_conf, _ = engine._rule_score(ind_strong)
        assert strong_conf >= weak_conf, (
            f"Expected strong ({strong_conf}) >= weak ({weak_conf})"
        )


# ── Ensemble Logic ───────────────────────────────────────────────────

class TestEnsemble:
    """Core ensemble test: weights (Rules 20%, RF 40%, LSTM 40%)."""

    def test_rules_only_all_models_unavailable(self, engine):
        """When both ML models are None, rules decide solo (100% weight)."""
        decision, confidence = engine._ensemble("BUY", 70, None, 0, None, 0)
        assert decision == "BUY"
        # Rules at 100% weight → BUY stays BUY
        assert confidence > 0

    def test_rules_only_both_low_confidence(self, engine):
        """When ML models have low confidence (< 0.5), rules decide solo."""
        decision, confidence = engine._ensemble("BUY", 70, "BUY", 0.3, "SELL", 0.2)
        assert decision == "BUY"

    def test_all_three_agree_buy(self, engine):
        """All 3 models agree on BUY → BUY with high confidence."""
        decision, confidence = engine._ensemble(
            "BUY", 80, "BUY", 0.8, "BUY", 0.75,
        )
        assert decision == "BUY"
        assert confidence >= 80, f"Expected high confidence on agreement, got {confidence}"

    def test_all_three_agree_sell(self, engine):
        """All 3 models agree on SELL → SELL with high confidence."""
        decision, confidence = engine._ensemble(
            "SELL", 75, "SELL", 0.7, "SELL", 0.8,
        )
        assert decision == "SELL"
        assert confidence >= 75

    def test_rf_overrides_rules_with_high_confidence(self, engine):
        """RF with high confidence and opposite sign from rules → ensemble should reflect RF's weight."""
        decision, confidence = engine._ensemble(
            "SELL", 60, "BUY", 0.9, None, 0,
        )
        # RF weight (0.4 * 0.9 = 0.36) + Rules (0.2) = 0.56 total
        # RF vote: +1 * 0.36 = +0.36, Rules: -1 * 0.2 = -0.2 → net = +0.16 / 0.56 = +0.29 → BUY or HOLD
        # avg_score = 0.16/0.56 ≈ 0.286 < 0.3 → HOLD
        assert decision == "HOLD", f"Expected HOLD (conflict), got {decision}"

    def test_rf_and_lstm_disagree_hold(self, engine):
        """RF and LSTM disagree → HOLD with lower confidence."""
        decision, confidence = engine._ensemble(
            "BUY", 60, "SELL", 0.8, "BUY", 0.7,
        )
        # RF: -1 * 0.4*0.8 = -0.32, LSTM: +1 * 0.4*0.7 = +0.28, Rules: +1 * 0.2 = +0.2
        # net = 0.16 / 0.92 ≈ 0.174 → HOLD
        assert decision == "HOLD"

    def test_both_ml_unavailable_rules_full_weight(self, engine):
        """No ML models available → rules get full weight."""
        decision, confidence = engine._ensemble("BUY", 65, None, 0, None, 0)
        assert decision == "BUY"
        assert confidence > 0

    def test_rules_sell_rf_buy_lstm_buy_eventual_hold(self, engine):
        """2-1 majority (BUY) → should lean BUY."""
        decision, confidence = engine._ensemble(
            "SELL", 70, "BUY", 0.75, "BUY", 0.7,
        )
        # RF: +1 * 0.3 + LSTM: +1 * 0.28 = +0.58, Rules: -1 * 0.2 = -0.2
        # net = 0.38 / 0.78 ≈ 0.487 → BUY (> 0.3)
        assert decision == "BUY"

    def test_all_three_agree_hold(self, engine):
        """All 3 models agree on HOLD → HOLD."""
        decision, confidence = engine._ensemble("HOLD", 50, "HOLD", 0.6, "HOLD", 0.55)
        assert decision == "HOLD"

    def test_no_votes_returns_hold(self, engine):
        """No votes at all → HOLD with 0 confidence."""
        # Force empty votes by having all None signals
        # This is an edge case that shouldn't happen in practice
        decision, confidence = engine._ensemble("HOLD", 0, "HOLD", 0, "HOLD", 0)
        assert decision == "HOLD"

    def test_lstm_alone_with_rules(self, engine):
        """LSTM available, RF unavailable → LSTM + Rules decide."""
        decision, confidence = engine._ensemble(
            "BUY", 80, None, 0, "BUY", 0.85,
        )
        assert decision == "BUY"
        assert confidence > 70

    def test_rf_alone_with_rules(self, engine):
        """RF available, LSTM unavailable → RF + Rules decide."""
        decision, confidence = engine._ensemble(
            "SELL", 70, "SELL", 0.9, None, 0,
        )
        assert decision == "SELL"


# ── Template Reasoning ───────────────────────────────────────────────

class TestTemplateReasoning:
    def test_buy_reasoning_includes_indicators(self, engine):
        text = engine._template_reasoning("BUY", 75, {
            "rsi": 28, "ema_fast": 100, "ema_slow": 90,
            "volume_ratio": 2.0,
        })
        assert "BUY" in text
        assert "RSI" in text
        assert "bullish" in text
        assert "volume" in text

    def test_sell_reasoning_includes_indicators(self, engine):
        text = engine._template_reasoning("SELL", 75, {
            "rsi": 75, "ema_fast": 90, "ema_slow": 100,
            "volume_ratio": 1.0,
        })
        assert "SELL" in text
        assert "RSI" in text
        assert "bearish" in text

    def test_hold_reasoning(self, engine):
        text = engine._template_reasoning("HOLD", 30, {"rsi": 50})
        assert "Mixed" in text or "HOLD" in text or "no clear" in text

    def test_buy_fallback_without_signals(self, engine):
        text = engine._template_reasoning("BUY", 55, {"rsi": 50, "volume_ratio": 1.0})
        assert "favours" in text or "upside" in text


# ── Full Analysis Pipeline ───────────────────────────────────────────

class TestAnalyze:
    def test_analyze_with_valid_data(self, engine, ohlcv):
        result = engine.analyze("BTC/USDT", ohlcv, "CRYPTO")
        assert result is not None
        assert result["symbol"] == "BTC/USDT"
        assert result["exchange"] == "CRYPTO"
        assert result["decision"] in ("BUY", "SELL", "HOLD")
        assert 0 <= result["confidence"] <= 100
        assert "model_breakdown" in result
        assert "indicators" in result
        assert "rsi" in result["indicators"]
        assert "price" in result
        assert result["price"] > 0

    def test_analyze_returns_structure(self, engine, ohlcv):
        result = engine.analyze("ETH/USDT", ohlcv, "BINANCE")
        assert result["symbol"] == "ETH/USDT"
        assert result["exchange"] == "BINANCE"
        assert isinstance(result["model_breakdown"], dict)
        assert "rule_based" in result["model_breakdown"]

    def test_analyze_empty_data_returns_none(self, engine):
        result = engine.analyze("BTC/USDT", [], "CRYPTO")
        assert result is None

    def test_analyze_too_few_candles_returns_none(self, engine):
        candles = [{"time": 1, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}]
        result = engine.analyze("BTC/USDT", candles * 10, "CRYPTO")
        assert result is None

    def test_analyze_handles_reversed_data(self, engine):
        """Engine should handle data sorted newest→oldest."""
        candles = []
        price = 50000
        for i in range(60):
            price += 30
            candles.append({
                "time": 1700000000 + (60 - i) * 900,  # newer first
                "open": round(price, 2),
                "high": round(price + 20, 2),
                "low": round(price - 20, 2),
                "close": round(price, 2),
                "volume": 1000,
            })
        # Newest first → engine should reverse
        result = engine.analyze("BTC/USDT", candles, "CRYPTO")
        assert result is not None
        assert result["decision"] in ("BUY", "SELL", "HOLD")

    def test_model_breakdown_includes_rule_based(self, engine, ohlcv):
        result = engine.analyze("BTC/USDT", ohlcv, "CRYPTO")
        mb = result["model_breakdown"]
        assert "rule_based" in mb
        rb = mb["rule_based"]
        assert "signal" in rb
        assert "confidence" in rb


# ── Crash Safety ─────────────────────────────────────────────────────

class TestCrashSafety:
    def test_analyze_never_crashes(self, engine):
        """analyze() should never raise — always return HOLD or None."""
        # Various bad inputs
        bad_inputs = [
            ("BTC", None, "CRYPTO"),
            ("BTC", [{"bad": "data"}] * 50, "CRYPTO"),
            ("BTC", [{"open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}] * 50, "CRYPTO"),
            ("BTC", "not a list", "CRYPTO"),
        ]
        for symbol, data, exchange in bad_inputs:
            try:
                result = engine.analyze(symbol, data, exchange)
                # Should either return None or a dict (never crash)
                assert result is None or isinstance(result, dict)
            except Exception as e:
                pytest.fail(f"analyze() crashed with input ({symbol}, {type(data).__name__}, {exchange}): {e}")

    def test_engine_initialises_without_crashing(self):
        """Engine constructor should never crash even on import failures."""
        try:
            e = StrategyEngine()
            assert e.name == "SilverTrade AI Strategy Engine"
        except Exception as e:
            pytest.fail(f"Engine constructor crashed: {e}")

    def test_confidence_range(self, engine, ohlcv):
        """Confidence should always be 0-100."""
        result = engine.analyze("BTC/USDT", ohlcv, "CRYPTO")
        if result:
            assert 0 <= result["confidence"] <= 100, f"Confidence out of range: {result['confidence']}"


# ── Edge Cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_analyze_with_zero_volume_data(self, engine):
        """Zero volume data shouldn't crash."""
        candles = []
        price = 100
        for i in range(60):
            candles.append({
                "time": i,
                "open": price, "high": price + 1, "low": price - 1,
                "close": price, "volume": 0,
            })
        result = engine.analyze("TEST/USDT", candles, "CRYPTO")
        assert result is not None

    def test_analyze_with_flat_prices(self, engine):
        """Flat prices (no movement) shouldn't crash."""
        candles = []
        for i in range(60):
            candles.append({
                "time": i,
                "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1000,
            })
        result = engine.analyze("FLAT/USDT", candles, "CRYPTO")
        assert result is not None
        assert result["decision"] in ("BUY", "SELL", "HOLD")

    def test_analyze_with_gap_data(self, engine):
        """Large price gaps shouldn't crash."""
        candles = []
        price = 100
        for i in range(60):
            if i == 30:
                price = 10000  # 100x gap
            price += 5
            candles.append({
                "time": i,
                "open": price, "high": price + 10, "low": price - 10,
                "close": price, "volume": 1000,
            })
        result = engine.analyze("VOLATILE/USDT", candles, "CRYPTO")
        assert result is not None
