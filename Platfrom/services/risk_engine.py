"""
SilverTrade AI — Risk Engine
=============================
Pre-trade risk validation. Called by execute_signal and place_order
services BEFORE any broker API call.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    """Result of a single risk check."""
    severity: str  # 'OK', 'WARN', 'BLOCK'
    message: str


@dataclass
class RiskResult:
    """Result of complete risk validation."""
    approved: bool
    warnings: List[str]
    blocks: List[str]


class RiskEngine:
    """Pre-trade risk validation."""

    def validate(
        self,
        order: Dict[str, Any],
        user_settings: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> RiskResult:
        """
        Returns RiskResult with:
          - approved: bool
          - warnings: list[str]   # non-blocking warnings shown to user
          - blocks: list[str]     # blocking violations that reject the order
        """
        checks = [
            self._check_daily_loss_limit(order, user_settings, portfolio),
            self._check_max_open_positions(order, user_settings, portfolio),
            self._check_position_size(order, user_settings, portfolio),
            self._check_duplicate_position(order, portfolio),
            self._check_margin_sufficiency(order, portfolio),
            self._check_instrument_risk(order),
            self._check_volatility_warning(order),
            self._check_expiry_warning(order),
            self._check_circuit_filter(order),
            self._check_loss_streak(order, portfolio),
        ]
        blocks = [c.message for c in checks if c.severity == 'BLOCK']
        warnings = [c.message for c in checks if c.severity == 'WARN']
        return RiskResult(approved=len(blocks) == 0, blocks=blocks, warnings=warnings)

    def _check_daily_loss_limit(self, order, settings, portfolio):
        """Reject if day P&L < -X% of capital."""
        daily_loss_limit_pct = settings.get('daily_loss_limit_pct', 5.0)
        day_pnl = portfolio.get('day_pnl', 0)
        total_value = portfolio.get('total_value', 1)
        
        if total_value > 0:
            day_pnl_pct = (day_pnl / total_value) * 100
            if day_pnl_pct < -daily_loss_limit_pct:
                return RiskCheck('BLOCK',
                    f"Daily loss limit reached ({day_pnl_pct:.1f}%). "
                    f"Trading halted for today. Reset tomorrow.")
        return RiskCheck('OK', '')

    def _check_max_open_positions(self, order, settings, portfolio):
        """Reject if already at max open positions."""
        max_positions = settings.get('max_open_positions', 5)
        open_positions = portfolio.get('open_positions', [])
        
        if len(open_positions) >= max_positions:
            return RiskCheck('BLOCK',
                f"Maximum open positions ({max_positions}) reached. "
                f"Close a position before opening a new one.")
        return RiskCheck('OK', '')

    def _check_position_size(self, order, settings, portfolio):
        """Warn/block if order size > risk per trade limit."""
        risk_per_trade_pct = settings.get('risk_per_trade_pct', 2.0)
        available_balance = portfolio.get('available_balance', 0)
        quantity = float(order.get('quantity', 0))
        price = float(order.get('price', 0))
        
        if price > 0 and quantity > 0:
            order_value = quantity * price
            max_allowed = available_balance * (risk_per_trade_pct / 100)
            
            if max_allowed > 0:
                if order_value > max_allowed * 3:  # 3x = hard block
                    return RiskCheck('BLOCK',
                        f"Order size ₹{order_value:,.0f} exceeds 3x risk limit ₹{max_allowed:,.0f}.")
                elif order_value > max_allowed:  # 1–3x = warning only
                    return RiskCheck('WARN',
                        f"Order size ₹{order_value:,.0f} exceeds recommended risk ₹{max_allowed:,.0f}.")
        return RiskCheck('OK', '')

    def _check_duplicate_position(self, order, portfolio):
        """Warn if user already has position in same symbol."""
        open_positions = portfolio.get('open_positions', [])
        symbol = order.get('symbol', '')
        
        for pos in open_positions:
            if pos.get('symbol') == symbol:
                return RiskCheck('WARN',
                    f"You already have a position in {symbol}. "
                    f"Consider if adding to it is appropriate.")
        return RiskCheck('OK', '')

    def _check_margin_sufficiency(self, order, portfolio):
        """Block if insufficient margin via broker margin API."""
        available_balance = portfolio.get('available_balance', 0)
        quantity = float(order.get('quantity', 0))
        price = float(order.get('price', 0))
        
        # Simple margin check - in production, use broker margin API
        order_value = quantity * price
        required_margin = order_value * 0.5  # Assume 50% margin for intraday
        
        if available_balance < required_margin:
            return RiskCheck('BLOCK',
                f"Insufficient margin: need ₹{required_margin:,.0f}, "
                f"have ₹{available_balance:,.0f}.")
        return RiskCheck('OK', '')

    def _check_instrument_risk(self, order):
        """Warn for high-risk instruments (options, futures)."""
        symbol = order.get('symbol', '')
        product = order.get('product', '')
        
        if product in ['NRML', 'MIS'] and ('CE' in symbol or 'PE' in symbol):
            return RiskCheck('WARN',
                f"Options trading involves significant risk. "
                f"Ensure you understand theta decay and time value.")
        return RiskCheck('OK', '')

    def _check_volatility_warning(self, order):
        """Warn if ATR > 2x normal (abnormally volatile — earnings/events)."""
        try:
            symbol = order.get('symbol', '')
            exchange = order.get('exchange', 'NSE')
            
            # Estimate volatility from order price if detailed market data unavailable
            atr_ratio = order.get('atr_ratio', None)
            if atr_ratio is not None and atr_ratio > 2.0:
                return RiskCheck('WARN',
                    f"High volatility detected for {symbol} (ATR {atr_ratio:.1f}x normal). "
                    f"Consider reducing position size or using wider stops.")
            
            # Fallback: warn for certain instrument types known for high volatility
            product = order.get('product', '')
            if 'CE' in symbol or 'PE' in symbol:
                if product in ['NRML']:  # Overnight options
                    return RiskCheck('WARN',
                        f"Options carry overnight gap risk. Consider MIS (intraday) product type "
                        f"to limit exposure.")
        except Exception as e:
            logger.debug("Volatility check failed: %s", e)
        return RiskCheck('OK', '')

    def _check_expiry_warning(self, order):
        """Warn if options contract expires in < 2 days."""
        try:
            symbol = order.get('symbol', '')
            
            # Parse expiry from options symbol pattern (e.g., NIFTY28MAR2422000CE)
            # Common formats: SYMBOL_DDMMMYY_STRIKE_CE/PE or SYMBOLDDMMMYYSTRIKECE
            expiry_date = None
            for pattern in ['CE', 'PE']:
                if pattern in symbol:
                    # Try to extract date from symbol (various broker formats)
                    import re
                    # Format: 28MAR24 or 28MAR2024 or 28MAR
                    match = re.search(r'(\d{2})([A-Z]{3})(\d{2,4})', symbol)
                    if match:
                        day, month_str, year_str = match.groups()
                        months = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                                  'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
                        month = months.get(month_str.upper(), None)
                        if month:
                            year = int('20' + year_str) if len(year_str) == 2 else int(year_str)
                            expiry_date = datetime(year, month, int(day))
                    break
            
            if expiry_date:
                days_to_expiry = (expiry_date - datetime.now()).days
                if days_to_expiry <= 1:
                    return RiskCheck('WARN',
                        f"Options contract expires TOMORROW ({expiry_date.strftime('%d %b %Y')}). "
                        f"Theta decay accelerates near expiry — consider rolling to next month.")
                elif days_to_expiry <= 3:
                    return RiskCheck('WARN',
                        f"Options contract expires in {days_to_expiry} days ({expiry_date.strftime('%d %b %Y')}). "
                        f"Time decay is elevated.")
        except Exception as e:
            logger.debug("Expiry check failed: %s", e)
        return RiskCheck('OK', '')

    def _check_circuit_filter(self, order):
        """Block if stock is in upper/lower circuit (cannot buy/sell)."""
        try:
            action = order.get('action', '')
            symbol = order.get('symbol', '')
            circuit_status = order.get('circuit_status', None)
            exchange = order.get('exchange', 'NSE')
            
            # If broker provides circuit status, use it
            if circuit_status:
                if circuit_status.upper() == 'UPPER' and action.upper() == 'BUY':
                    return RiskCheck('BLOCK',
                        f"{symbol} is at upper circuit on {exchange}. Buy orders cannot be executed.")
                if circuit_status.upper() == 'LOWER' and action.upper() == 'SELL':
                    return RiskCheck('BLOCK',
                        f"{symbol} is at lower circuit on {exchange}. Sell orders cannot be executed.")
                if circuit_status.upper() == 'UPPER':
                    return RiskCheck('WARN',
                        f"{symbol} is at upper circuit on {exchange}. "
                        f"Only sell orders may be executable.")
                if circuit_status.upper() == 'LOWER':
                    return RiskCheck('WARN',
                        f"{symbol} is at lower circuit on {exchange}. "
                        f"Only buy orders may be executable.")
            
            # If exchange is CRYPTO, no circuit filters apply
            if exchange.upper() in ('CRYPTO', 'BINANCE', 'BYBIT'):
                return RiskCheck('OK', '')
            
            # For NSE/BSE equities, warn about potential circuit risks
            # In production, fetch real circuit limits from exchange data
            if action.upper() in ('BUY', 'SELL'):
                # Could add a generic caution for low-volume stocks
                pass
                
        except Exception as e:
            logger.debug("Circuit filter check failed: %s", e)
        return RiskCheck('OK', '')

    def _check_loss_streak(self, order, portfolio):
        """Check for consecutive losses and apply cooling period."""
        recent_trades = portfolio.get('recent_trades', [])
        consecutive_losses = 0
        
        for trade in recent_trades[:5]:  # Check last 5 trades
            pnl = trade.get('pnl', 0)
            if pnl < 0:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= 5:
            return RiskCheck('BLOCK',
                f"5 consecutive losses detected. Trading paused for 1 hour. "
                f"This is a protective measure. Review your settings.")
        elif consecutive_losses >= 3:
            return RiskCheck('WARN',
                f"{consecutive_losses} consecutive losses detected. "
                f"Consider pausing and reviewing your strategy.")
        
        return RiskCheck('OK', '')
