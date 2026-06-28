"""
Bybit order/position data mapping to SilverTrade AI internal format.

Normalizes Bybit REST API response fields to SilverTrade AI field names.

Bybit order fields (from /v5/order/realtime and /v5/order/history):
    orderId       – string order ID
    symbol        – trading pair
    side          – "Buy" | "Sell"
    orderType     – "Market" | "Limit" | "StopLoss" | "TakeProfit"
    orderStatus   – "New" | "Filled" | "PartiallyFilledCanceled" | "Cancelled" | "Rejected"
    price         – limit price (string)
    triggerPrice  – stop price (string)
    qty           – original quantity (string)
    cumExecQty    – filled quantity (string)
    cumExecValue  – cumulative executed value (string)
    createdTime   – creation timestamp (epoch ms)
    updatedTime   – last update timestamp (epoch ms)

Bybit fill fields (from /v5/execution/list):
    execId        – execution ID
    symbol        – trading pair
    orderId       – order ID
    execPrice     – execution price
    execQty       – executed quantity
    execType      – "Trade", "Funding", "AdlTrade"
    side          – "Buy" | "Sell"
    execTime      – execution timestamp

Bybit position fields (from /v5/position/list for linear futures):
    symbol        – trading pair
    size          – position size
    avgPrice      – average entry price
    unrealisedPnl – unrealized P&L
    realisedPnl   – realized P&L
"""

from database.token_db import get_oa_symbol, get_symbol, get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)


def map_order_data(order_data):
    """
    Normalise a list of Bybit order dicts to SilverTrade AI internal format.
    """
    try:
        if order_data is None:
            return []
        if isinstance(order_data, dict) and "retCode" in order_data:
            return []
        if isinstance(order_data, str):
            return []
        if not isinstance(order_data, list):
            return []

        for order in order_data:
            if not isinstance(order, dict):
                continue

            order["orderId"] = str(order.get("orderId", ""))
            order["tradingSymbol"] = order.get("symbol", "")
            order["exchangeSegment"] = "CRYPTO"
            order["productType"] = "CNC"

            # Side
            side = order.get("side", "")
            order["transactionType"] = side.upper()  # "BUY" | "SELL"

            # Order type mapping
            raw_type = order.get("orderType", "")
            if raw_type in ("Market", "market_order", "MARKET"):
                order["orderType"] = "MARKET"
            elif raw_type in ("Limit", "limit_order", "LIMIT"):
                order["orderType"] = "LIMIT"
            elif raw_type in ("StopLoss", "stop_loss", "STOP_LOSS"):
                order["orderType"] = "SL"
            elif raw_type in ("TakeProfit", "take_profit", "TAKE_PROFIT"):
                order["orderType"] = "SL"
            else:
                order["orderType"] = raw_type.upper()

            # Status mapping
            status = order.get("orderStatus", "")
            if status in ("New", "Active"):
                order["orderStatus"] = "open"
            elif status in ("Filled", "PartiallyFilled"):
                order["orderStatus"] = "complete"
            elif status in ("Cancelled", "Canceled"):
                order["orderStatus"] = "cancelled"
            elif status in ("Rejected", "Deactivated"):
                order["orderStatus"] = "rejected"
            elif status == "PartiallyFilledCanceled":
                order["orderStatus"] = "cancelled"
            else:
                order["orderStatus"] = status.lower()

            # Numeric fields
            order["quantity"] = float(order.get("qty", 0))
            order["filledQuantity"] = float(order.get("cumExecQty", 0))
            order["price"] = float(order.get("price", 0))
            order["triggerPrice"] = float(order.get("triggerPrice", 0))
            order["updateTime"] = order.get("updatedTime", order.get("createdTime", ""))

        return order_data

    except Exception as e:
        logger.error(f"Exception in map_order_data: {e}")
        return []


def calculate_order_statistics(order_data):
    """Calculate statistics from order data."""
    try:
        if not order_data or not isinstance(order_data, list):
            return {
                "total_buy_orders": 0,
                "total_sell_orders": 0,
                "total_completed_orders": 0,
                "total_open_orders": 0,
                "total_rejected_orders": 0,
            }

        total_buy = total_sell = total_completed = total_open = total_rejected = 0

        for order in order_data:
            if not isinstance(order, dict):
                continue
            if order.get("transactionType") == "BUY":
                total_buy += 1
            elif order.get("transactionType") == "SELL":
                total_sell += 1
            status = order.get("orderStatus", "").lower()
            if status in ("complete", "filled"):
                total_completed += 1
            elif status in ("open", "new", "active"):
                total_open += 1
            elif status == "rejected":
                total_rejected += 1

        return {
            "total_buy_orders": total_buy,
            "total_sell_orders": total_sell,
            "total_completed_orders": total_completed,
            "total_open_orders": total_open,
            "total_rejected_orders": total_rejected,
        }

    except Exception as e:
        logger.error(f"Exception in calculate_order_statistics: {e}")
        return {
            "total_buy_orders": 0,
            "total_sell_orders": 0,
            "total_completed_orders": 0,
            "total_open_orders": 0,
            "total_rejected_orders": 0,
        }


def transform_order_data(orders):
    """Transform mapped order data to SilverTrade AI standard format."""
    try:
        if orders is None:
            return []
        if isinstance(orders, dict):
            orders = [orders]
        if not isinstance(orders, list):
            return []

        transformed = []
        for order in orders:
            if not isinstance(order, dict):
                continue

            order_type = order.get("orderType", "").upper()
            if order_type == "SL":
                pricetype = "SL"
            elif order_type in ("MARKET", "LIMIT"):
                pricetype = order_type
            else:
                pricetype = order_type

            qty = float(order.get("quantity", 0))
            filled = float(order.get("filledQuantity", 0))
            remaining = qty - filled

            transformed.append(
                {
                    "symbol": order.get("tradingSymbol", ""),
                    "exchange": order.get("exchangeSegment", ""),
                    "action": order.get("transactionType", ""),
                    "quantity": remaining,
                    "filled_quantity": filled,
                    "price": float(order.get("price", 0.0)),
                    "trigger_price": float(order.get("triggerPrice", 0.0)),
                    "pricetype": pricetype,
                    "product": order.get("productType", "CNC"),
                    "orderid": order.get("orderId", ""),
                    "order_status": order.get("orderStatus", ""),
                    "timestamp": str(order.get("updateTime", "")),
                }
            )

        return transformed

    except Exception as e:
        logger.error(f"Exception in transform_order_data: {e}")
        return []


def map_trade_data(trade_data):
    """
    Normalise a list of Bybit execution entries to SilverTrade AI internal format.
    """
    try:
        if trade_data is None:
            return []
        if isinstance(trade_data, dict) and "retCode" in trade_data:
            return []
        if isinstance(trade_data, str):
            return []
        if not isinstance(trade_data, list):
            return []

        for trade in trade_data:
            if not isinstance(trade, dict):
                continue

            trade["tradingSymbol"] = trade.get("symbol", "")
            trade["exchangeSegment"] = "CRYPTO"
            trade["productType"] = "CNC"
            trade["orderId"] = str(trade.get("orderId", ""))
            trade["tradedQuantity"] = float(trade.get("execQty", 0))
            trade["tradedPrice"] = float(trade.get("execPrice", 0))
            side = trade.get("side", "")
            trade["transactionType"] = side.upper()
            trade["updateTime"] = trade.get("execTime", "")

        return trade_data

    except Exception as e:
        logger.error(f"Exception in map_trade_data: {e}")
        return []


def transform_tradebook_data(tradebook_data):
    """Transform Bybit trade data to SilverTrade AI standard format."""
    try:
        if not tradebook_data or not isinstance(tradebook_data, list):
            return []

        transformed = []
        for trade in tradebook_data:
            if not isinstance(trade, dict):
                continue

            qty = float(trade.get("tradedQuantity", 0))
            price = float(trade.get("tradedPrice", 0))

            transformed.append(
                {
                    "symbol": trade.get("tradingSymbol", ""),
                    "exchange": trade.get("exchangeSegment", ""),
                    "product": trade.get("productType", ""),
                    "action": trade.get("transactionType", ""),
                    "quantity": qty,
                    "average_price": price,
                    "trade_value": qty * price,
                    "orderid": trade.get("orderId", ""),
                    "timestamp": str(trade.get("updateTime", "")),
                }
            )

        return transformed

    except Exception as e:
        logger.error(f"Exception in transform_tradebook_data: {e}")
        return []


def map_position_data(position_data):
    """
    Normalise a list of Bybit position/balance dicts to SilverTrade AI format.
    """
    try:
        if position_data is None:
            return []
        if isinstance(position_data, dict) and "retCode" in position_data:
            return []
        if isinstance(position_data, str):
            return []
        if not isinstance(position_data, list):
            return []

        processed = []
        for position in position_data:
            if not isinstance(position, dict):
                continue

            asset = position.get("asset", "")
            free = float(position.get("free", 0))
            locked = float(position.get("locked", 0))
            total = free + locked

            if total <= 0:
                continue

            position["tradingSymbol"] = f"{asset}USDT"
            position["exchangeSegment"] = "CRYPTO"
            position["productType"] = "CNC"
            position["netQty"] = total
            position["avgCostPrice"] = 0.0
            position["lastTradedPrice"] = 0.0
            position["marketValue"] = 0.0
            position["pnlAbsolute"] = 0.0
            position["lot_size"] = float(position.get("lot_size", 1.0))
            position["multiplier"] = 1
            position["positionType"] = "open" if total != 0 else "closed"

            processed.append(position)

        return processed

    except Exception as e:
        logger.error(f"Exception in map_position_data: {e}")
        return []


def transform_positions_data(positions_data):
    """Transform positions data to SilverTrade AI standard format."""
    try:
        if not positions_data or not isinstance(positions_data, list):
            return []

        transformed = []
        for position in positions_data:
            if not isinstance(position, dict):
                continue

            transformed.append(
                {
                    "symbol": position.get("tradingSymbol", ""),
                    "exchange": position.get("exchangeSegment", ""),
                    "product": position.get("productType", ""),
                    "quantity": position.get("netQty", 0),
                    "average_price": float(position.get("avgCostPrice", 0.0)),
                    "ltp": float(position.get("lastTradedPrice", 0.0)),
                    "pnl": float(position.get("pnlAbsolute", 0.0)),
                    "lot_size": float(position.get("lot_size", 1.0)),
                }
            )

        return transformed

    except Exception as e:
        logger.error(f"Exception in transform_positions_data: {e}")
        return []


def transform_holdings_data(holdings_data):
    """Transform holdings data to SilverTrade AI format."""
    try:
        if not holdings_data or not isinstance(holdings_data, list):
            return []

        transformed = []
        for holding in holdings_data:
            if not isinstance(holding, dict):
                continue
            transformed.append(
                {
                    "symbol": holding.get("tradingSymbol", holding.get("symbol", "")),
                    "exchange": holding.get("exchangeSegment", "CRYPTO"),
                    "quantity": holding.get("totalQty", holding.get("total_qty", 0)),
                    "product": "CNC",
                    "pnl": holding.get("pnlAbsolute", 0.0),
                    "pnlpercent": holding.get("pnlPercent", 0.0),
                }
            )

        return transformed

    except Exception as e:
        logger.error(f"Exception in transform_holdings_data: {e}")
        return []


def map_portfolio_data(portfolio_data):
    """Process portfolio data for Bybit (no equity holdings — pass through)."""
    try:
        if not portfolio_data or not isinstance(portfolio_data, list):
            return []
        return portfolio_data
    except Exception as e:
        logger.error(f"Exception in map_portfolio_data: {e}")
        return []


def calculate_portfolio_statistics(holdings_data):
    """Calculate portfolio statistics from holdings data."""
    try:
        if not holdings_data or not isinstance(holdings_data, list):
            return {
                "totalholdingvalue": 0.0,
                "totalinvvalue": 0.0,
                "totalprofitandloss": 0.0,
                "totalpnlpercentage": 0.0,
            }

        total_value = sum(
            float(h.get("marketValue", h.get("lastTradedPrice", 0)) * h.get("totalQty", 0))
            for h in holdings_data
            if isinstance(h, dict)
        )
        total_inv = sum(
            float(h.get("avgCostPrice", 0)) * h.get("totalQty", 0)
            for h in holdings_data
            if isinstance(h, dict)
        )
        total_pnl = sum(
            float(h.get("pnlAbsolute", 0)) for h in holdings_data if isinstance(h, dict)
        )

        return {
            "totalholdingvalue": round(total_value, 2),
            "totalinvvalue": round(total_inv, 2),
            "totalprofitandloss": round(total_pnl, 2),
            "totalpnlpercentage": round((total_pnl / total_inv * 100) if total_inv > 0 else 0, 2),
        }

    except Exception as e:
        logger.error(f"Exception in calculate_portfolio_statistics: {e}")
        return {
            "totalholdingvalue": 0.0,
            "totalinvvalue": 0.0,
            "totalprofitandloss": 0.0,
            "totalpnlpercentage": 0.0,
        }
