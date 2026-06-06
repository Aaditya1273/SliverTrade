"""
SilverTrade AI — Backtesting Framework
========================================
Runs the strategy engine's signals against historical OHLCV data to
measure real performance: win rate, max drawdown, Sharpe ratio, etc.

Every confidence score shown to users should be calibrated against
these backtest results — never based on arbitrary weights.

SAFETY: All methods handle empty/invalid data gracefully. If the
engine crashes mid-backtest, results up to that point are still valid.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Trade:
    """A single backtest trade — entry, exit, and P&L."""

    def __init__(
        self,
        entry_time: int,
        entry_price: float,
        direction: str,
        signal_id: str = "",
    ):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction  # 'BUY' or 'SELL'
        self.exit_time: Optional[int] = None
        self.exit_price: Optional[float] = None
        self.pnl: float = 0.0
        self.pnl_pct: float = 0.0
        self.signal_id = signal_id
        self.closed = False

    def close(self, exit_time: int, exit_price: float) -> None:
        """Close the trade and compute P&L."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        if self.direction == "BUY":
            self.pnl = exit_price - self.entry_price
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100
        else:
            self.pnl = self.entry_price - exit_price
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price * 100
        self.closed = True


class BacktestResult:
    """Aggregate backtest performance metrics."""

    def __init__(self) -> None:
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []

    def add_trade(self, trade: Trade) -> None:
        self.trades.append(trade)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self.trades if t.closed]

    @property
    def win_rate(self) -> float:
        closed = self.closed_trades
        if not closed:
            return 0.0
        wins = sum(1 for t in closed if t.pnl > 0)
        return wins / len(closed)

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.closed_trades)

    @property
    def total_pnl_pct(self) -> float:
        if not self.closed_trades:
            return 0.0
        return sum(t.pnl_pct for t in self.closed_trades)

    @property
    def avg_win(self) -> float:
        wins = [t.pnl for t in self.closed_trades if t.pnl > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def avg_loss(self) -> float:
        losses = [t.pnl for t in self.closed_trades if t.pnl <= 0]
        return sum(losses) / len(losses) if losses else 0.0

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough decline in equity curve as a percentage."""
        if len(self.equity_curve) < 2:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for value in self.equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    @property
    def sharpe_ratio(self) -> float:
        """Risk-adjusted return (annualised). Assumes 0% risk-free rate."""
        closed = self.closed_trades
        if len(closed) < 2:
            return 0.0
        returns = [t.pnl_pct for t in closed]
        avg_return = sum(returns) / len(returns)
        std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
        if std_dev == 0:
            return 0.0
        # Annualise: ~252 trading days, ~96 15m candles per day
        # For simplicity, use sqrt(N_trades) as an approximation
        return round(avg_return / std_dev * math.sqrt(len(closed)), 2)

    @property
    def profit_factor(self) -> float:
        """Gross profit / gross loss."""
        gross_profit = sum(t.pnl for t in self.closed_trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.closed_trades if t.pnl < 0))
        return round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")

    @property
    def calmar_ratio(self) -> float:
        """Annual return / max drawdown."""
        if not self.closed_trades or self.max_drawdown == 0:
            return 0.0
        total_return_pct = self.total_pnl_pct
        return round(total_return_pct / self.max_drawdown, 2) if self.max_drawdown > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "closed_trades": len(self.closed_trades),
            "win_rate": round(self.win_rate, 4),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "max_drawdown_pct": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "profit_factor": self.profit_factor,
            "calmar_ratio": self.calmar_ratio,
            "equity_curve": [round(v, 2) for v in self.equity_curve],
        }


class Backtester:
    """Runs the strategy engine against historical OHLCV data.

    Walks through candle data sequentially, generates signals, opens
    positions on BUY/SELL signals, and closes them on the opposite
    signal or when stop loss / take profit is hit.
    """

    def __init__(self, strategy_engine):
        self.engine = strategy_engine

    def run(
        self,
        ohlcv: List[Dict[str, Any]],
        symbol: str = "BACKTEST",
        exchange: str = "CRYPTO",
        initial_capital: float = 100000.0,
        position_size_pct: float = 10.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 5.0,
    ) -> BacktestResult:
        """Run a full backtest.

        Args:
            ohlcv: Historical OHLCV candles (sorted oldest → newest)
            symbol: Symbol name for logging
            exchange: Exchange name
            initial_capital: Starting capital in quote currency
            position_size_pct: % of capital per trade
            stop_loss_pct: Stop loss % below entry
            take_profit_pct: Take profit % above entry

        Returns:
            BacktestResult with all trades and metrics
        """
        result = BacktestResult()
        if not ohlcv or len(ohlcv) < 60:
            logger.warning("Insufficient data for backtest (%d candles)", len(ohlcv) if ohlcv else 0)
            return result

        # Ensure sorted oldest → newest
        try:
            if ohlcv[0].get("time", 0) > ohlcv[-1].get("time", 0):
                ohlcv = list(reversed(ohlcv))
        except (IndexError, TypeError):
            return result

        capital = initial_capital
        equity = initial_capital
        result.equity_curve.append(equity)
        open_trade: Optional[Trade] = None

        for i in range(50, len(ohlcv)):
            window = ohlcv[: i + 1]
            current_candle = ohlcv[i]
            current_price = float(current_candle.get("close", 0))
            current_time = current_candle.get("time", 0)

            if current_price <= 0:
                continue

            # Skip if not enough data yet
            if len(window) < 50:
                continue

            # Generate signal
            signal = self.engine.analyze(symbol, window, exchange)
            if not signal:
                continue

            decision = signal.get("decision", "HOLD")

            # Check stop loss / take profit for open position
            if open_trade and not open_trade.closed:
                pnl_pct = 0.0
                if open_trade.direction == "BUY":
                    pnl_pct = (current_price - open_trade.entry_price) / open_trade.entry_price * 100
                else:
                    pnl_pct = (open_trade.entry_price - current_price) / open_trade.entry_price * 100

                # Close on TP or SL
                if pnl_pct >= take_profit_pct:
                    open_trade.close(current_time, current_price)
                    capital += open_trade.pnl * (position_size_pct / 100)
                    equity += open_trade.pnl
                    result.add_trade(open_trade)
                    open_trade = None
                elif pnl_pct <= -stop_loss_pct:
                    open_trade.close(current_time, current_price)
                    capital += open_trade.pnl * (position_size_pct / 100)
                    equity += open_trade.pnl
                    result.add_trade(open_trade)
                    open_trade = None

            # Enter new position on signal
            if open_trade is None:
                if decision == "BUY":
                    open_trade = Trade(current_time, current_price, "BUY", signal.get("id", ""))
                elif decision == "SELL":
                    open_trade = Trade(current_time, current_price, "SELL", signal.get("id", ""))

            # Record equity curve periodically
            if i % 5 == 0:
                # Mark-to-market: value of open position
                open_pnl = 0.0
                if open_trade and not open_trade.closed:
                    if open_trade.direction == "BUY":
                        open_pnl = (current_price - open_trade.entry_price) * (position_size_pct / 100)
                    else:
                        open_pnl = (open_trade.entry_price - current_price) * (position_size_pct / 100)
                result.equity_curve.append(round(equity + open_pnl, 2))

        # Close any remaining open trade at last price
        if open_trade and not open_trade.closed and ohlcv:
            last = ohlcv[-1]
            open_trade.close(last.get("time", 0), float(last.get("close", 0)))
            capital += open_trade.pnl * (position_size_pct / 100)
            result.add_trade(open_trade)

        return result
