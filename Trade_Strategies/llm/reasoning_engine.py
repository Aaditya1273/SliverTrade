"""
SilverTrade AI — LLM Reasoning Engine
=======================================
Generates human-readable, number-rich explanations for trading signals
using an LLM (GPT-4o-mini by default).

SAFETY:
- Falls back to template-based reasoning when LLM is unavailable.
- Caches identical indicator snapshots via in-memory dict (Redis in Phase 9).
- Never generates LLM reasoning for HOLD signals (cost optimisation).
- Hard timeout of 5 seconds per LLM call.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SilverTrade AI, a trading signal reasoning engine.
Your job is to explain WHY a trading signal was generated using the exact
indicator values provided. Rules you MUST follow:

1. Reference SPECIFIC numbers from the indicator data — never speak in generalities.
2. Keep explanations to 2-3 sentences maximum. Be dense, not verbose.
3. Use trading terminology naturally (oversold, divergence, resistance, etc.).
4. If the signal is BUY or SELL, mention the KEY risk factor (e.g., "resistance at $64,200").
5. Never promise future returns. Say "historically" or "the pattern suggests".
6. Never mention "I" or "my analysis" — phrase as objective observation.
7. For HOLD signals: return empty string (use template reasoning instead)."""


class LLMReasoningEngine:
    """Generates LLM-powered trading signal explanations.

    Uses OpenAI GPT-4o-mini (fast, cheap, good-enough). Falls back to
    template-based reasoning when the API is unavailable or the call fails.

    Indentical indicator snapshots are cached in-memory for 5 minutes
    to avoid duplicate API costs.
    """

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.client = None
        self.model = "gpt-4o-mini"
        self._cache: Dict[str, tuple] = {}  # cache_key → (timestamp, result)
        self._cache_ttl = 300  # 5 minutes
        self._initialised = False
        self._init_client()

    def _init_client(self) -> None:
        """Initialise the LLM client. No-op if API key is not set."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.info("OPENAI_API_KEY not set — LLM reasoning disabled (template fallback)")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self._initialised = True
            logger.info("LLM reasoning engine initialised (%s / %s)", self.provider, self.model)
        except ImportError:
            logger.warning("openai package not installed — LLM reasoning disabled")
        except Exception as e:
            logger.error("Failed to initialise LLM client: %s", e)

    @property
    def available(self) -> bool:
        """Whether the LLM client is ready to generate reasoning."""
        return self._initialised and self.client is not None

    def _cache_key(self, signal: str, confidence: float, indicators: dict) -> str:
        """Build a cache key from the signal + indicator values."""
        relevant = {k: round(v, 2) if isinstance(v, float) else v for k, v in indicators.items() if v is not None}
        raw = f"{signal}|{confidence:.1f}|{json.dumps(relevant, sort_keys=True)}"
        return str(hash(raw))

    def _get_cached(self, key: str) -> Optional[str]:
        """Return cached reasoning if it exists and is fresh."""
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, result = entry
        if time.time() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return result

    def _set_cache(self, key: str, result: str) -> None:
        """Store reasoning in cache, evicting old entries if cache is full."""
        if len(self._cache) > 500:
            # Remove oldest entries (simple approach)
            cutoff = time.time() - self._cache_ttl
            self._cache = {k: v for k, v in self._cache.items() if v[0] > cutoff}
        self._cache[key] = (time.time(), result)

    def _build_prompt(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        indicators: Dict[str, Any],
        model_breakdown: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a structured prompt for the LLM with real indicator values."""
        ind_parts = [f"  - {k}: {v}" for k, v in indicators.items() if v is not None]
        ind_section = "\n".join(ind_parts) if ind_parts else "  (none)"

        model_parts = []
        if model_breakdown:
            for model_name, data in model_breakdown.items():
                if isinstance(data, dict):
                    direction = data.get("direction", data.get("signal", "?"))
                    conf = data.get("confidence", 0)
                    model_parts.append(f"  - {model_name}: {direction} ({conf:.0f}%)")
                else:
                    model_parts.append(f"  - {model_name}: {data}")
        model_section = "\n".join(model_parts) if model_parts else "  Rule-based technical analysis"

        return (
            f"Generate a 2-3 sentence trading rationale for this signal:\n"
            f"\n"
            f"Symbol: {symbol}\n"
            f"Signal: {signal}\n"
            f"Confidence: {confidence:.1f}%\n"
            f"\n"
            f"Indicator Values:\n"
            f"{ind_section}\n"
            f"\n"
            f"Model Breakdown:\n"
            f"{model_section}\n"
            f"\n"
            f"Write 2-3 sentences explaining the technical basis for this signal.\n"
            f"Reference specific numbers. Mention one key risk factor."
        )

    def generate_reasoning(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        indicators: Dict[str, Any],
        model_breakdown: Optional[Dict[str, Any]] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate an LLM-powered explanation for a trading signal.

        Args:
            symbol: Trading pair symbol
            signal: BUY / SELL / HOLD
            confidence: Confidence score (0–100)
            indicators: Dict of indicator values
            model_breakdown: Per-model prediction breakdown (optional)
            market_context: Additional market context (optional)

        Returns:
            Human-readable reasoning string. Falls back to template on failure.
        """
        # HOLD signals use templates — no LLM cost
        if signal == "HOLD":
            return "Mixed signals with no clear directional bias. Multiple indicators are neutral or conflicting."

        # Check cache
        cache_key = self._cache_key(signal, confidence, indicators)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # If LLM not available, return template
        if not self.available:
            return self._template_reasoning(signal, indicators)

        # Call LLM with timeout
        try:
            prompt = self._build_prompt(symbol, signal, confidence, indicators, model_breakdown)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                temperature=0.3,
                timeout=10,
            )
            reasoning = response.choices[0].message.content.strip()
            if reasoning:
                self._set_cache(cache_key, reasoning)
                return reasoning
        except Exception as e:
            logger.warning("LLM reasoning failed: %s — using template fallback", e)

        return self._template_reasoning(signal, indicators)

    def _template_reasoning(self, signal: str, indicators: Dict[str, Any]) -> str:
        """Template-based reasoning fallback when LLM is unavailable.

        Uses the same indicator values to generate a reasonable explanation
        without any API call.
        """
        parts = []
        rsi = indicators.get("rsi")
        if rsi is not None:
            if signal == "BUY" and rsi < 30:
                parts.append(f"RSI deeply oversold at {rsi:.1f}")
            elif signal == "SELL" and rsi > 70:
                parts.append(f"RSI overbought at {rsi:.1f}")

        ema_fast = indicators.get("ema_9")
        ema_slow = indicators.get("ema_21")
        if ema_fast is not None and ema_slow is not None:
            if ema_fast > ema_slow:
                parts.append(f"bullish EMA crossover (9={ema_fast:.0f} > 21={ema_slow:.0f})")
            else:
                parts.append(f"bearish EMA crossover (9={ema_fast:.0f} < 21={ema_slow:.0f})")

        bb_lower = indicators.get("bb_lower")
        bb_upper = indicators.get("bb_upper")
        price = indicators.get("price")
        if price is not None and bb_lower is not None and price <= bb_lower:
            parts.append("price at lower Bollinger Band support")
        if price is not None and bb_upper is not None and price >= bb_upper:
            parts.append("price at upper Bollinger Band resistance")

        volume_ratio = indicators.get("volume_ratio")
        if volume_ratio is not None and volume_ratio > 1.5:
            parts.append(f"volume {volume_ratio:.1f}x above average confirming momentum")

        if not parts:
            if signal == "BUY":
                parts.append("technical indicators show favourable conditions")
            else:
                parts.append("technical indicators suggest caution")

        return f"{signal} signal: {'. '.join(parts)}."
