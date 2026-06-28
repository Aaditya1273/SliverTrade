"""
Binance order/position data mapping to SilverTrade AI internal format.

Normalizes Binance REST API response fields (snake_case Binance format
or camelCase Binance format) to SilverTrade AI internal field names.

References:
  https://binance-docs.github.io/apidocs/spot/en/#account-information-user_data
  https://binance-docs.github.io/apidocs/spot/en/#query-order-user_data
"""

from database.token_db import get_oa_symbol, get_symbol, get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)


def map_order_data(order_data):
    """
    Normalise a list of Binance order dicts to SilverTrade AI internal format.

    Binance order fields used:
        orderId          – integer order ID
        symbol           – trading pair (e.g. "BTCUSDT")
        side             – "BUY" | "SELL"
        type             – "LIMIT" | "MARKET" | "STOP_LOSS" | etc.
        status           – "NEW" | "FILLED" | "PARTIALLY_FILLED" | "CANCELED" | "REJECTED" | "EXPIRED"
        price            – limit price (string)
        stopPrice        – stop trigger price (string)
        origQty          – original quantity (string)
        executedQty      – filled quantity (string)
        cummulativeQuoteQty – cumulative quote asset quantity (string)
        time             – order creation timestamp (epoch ms)
        updateTime       – last update timestamp (epoch ms)
    """
    try:
        if order_data is None:
            return []
        if isinstance(order_data, dict) and "code" in order_data:
            logger.error(f"Error in order data: {order_data.get('msg', 'Unknown error')}")
            return []
        if isinstance(order_data, str):
            logger.error(f"Received string instead of order list: {order_data[:200]}")
            return []
        if not isinstance(order_data, list):
            logger.warning(f"Expected list, got {type(order_data)}")
            return []

        for order in order_data:
            if not isinstance(order, dict):
                continue

            raw_id = order.get("orderId", "")
            symbol = order.get("symbol", "")

            order["orderId"] = str(raw_id)
            order["tradingSymbol"] = symbol
            order["exchangeSegment"] = "CRYPTO"
            order["productType"] = "CNC"

            # Transaction type
            order["transactionType"] = order.get("side", "").upper()

            # Order type mapping
            raw_type = order.get("type", "").upper()
            if raw_type == "MARKET":
                order["orderType"] = "MARKET"
            elif raw_type == "LIMIT":
                order["orderType"] = "LIMIT"
            elif raw_type in ("STOP_LOSS", "STOP_LOSS_LIMIT"):
                order["orderType"] = "SL"
            elif raw_type in ("TAKE_PROFIT", "TAKE_PROFIT_LIMIT"):
                order["orderType"] = "SL"  # Treat as SL-like
            elif raw_type == "LIMIT_MAKER":
                order["orderType"] = "LIMIT"
            else:
                order["orderType"] = raw_type

            # Status mapping
            status = order.get("status", "").upper()
            if status == "NEW":
                order["orderStatus"] = "open"
            elif status in ("FILLED", "PARTIALLY_FILLED"):
                order["orderStatus"] = "complete"
            elif status == "CANCELED":
                order["orderStatus"] = "cancelled"
            elif status == "REJECTED":
                order["orderStatus"] = "rejected"
            elif status == "EXPIRED":
                order["orderStatus"] = "cancelled"
            elif status == "PENDING_CANCEL":
                order["orderStatus"] = "open"
            else:
                order["orderStatus"] = status.lower()

            # Numeric fields
            order["quantity"] = float(order.get("origQty", 0))
            order["filledQuantity"] = float(order.get("executedQty", 0))
            order["price"] = float(order.get("price", 0))
            order["triggerPrice"] = float(order.get("stopPrice", 0))
            order["updateTime"] = order.get("updateTime", order.get("time", ""))

        return order_data

    except Exception as e:
        logger.error(f"Exception in map_order_data: {e}")
        return []


def calculate_order_statistics(order_data):
    """
    Calculate statistics from order data.

    Returns dict with counts of buy/sell/completed/open/rejected orders.
    """
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
            elif status in ("open", "new"):
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
    """
    Transform mapped order data to SilverTrade AI standard format.
    """
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
            elif order_type == "SL-M":
                pricetype = "SL-M"
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
    Normalise a list of Binance myTrades entries to SilverTrade AI internal format.

    Binance trade fields:
        symbol    – trading pair
        id        – trade ID
        orderId   – order ID
        price     – execution price (string)
        qty       – traded quantity (string)
        quoteQty  – quote asset quantity (string)
        commission – fee paid
        time      – timestamp (epoch ms)
        isBuyer   – bool
    """
    try:
        if trade_data is None:
            return []
        if isinstance(trade_data, dict) and "code" in trade_data:
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
            trade["tradedQuantity"] = float(trade.get("qty", 0))
            trade["tradedPrice"] = float(trade.get("price", 0))
            trade["transactionType"] = "BUY" if trade.get("isBuyer") else "SELL"
            trade["updateTime"] = trade.get("time", "")

        return trade_data

    except Exception as e:
        logger.error(f"Exception in map_trade_data: {e}")
        return []


def transform_tradebook_data(tradebook_data):
    """Transform Binance trade/fill data to SilverTrade AI standard format."""
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
    Normalise a list of Binance position/balance dicts to SilverTrade AI format.

    Binance /api/v3/account → balances[] fields:
        asset  – asset symbol (e.g. "BTC")
        free   – available balance (string)
        locked – locked in orders (string)
    """
    try:
        if position_data is None:
            return []
        if isinstance(position_data, dict) and "code" in position_data:
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
            position["avgCostPrice"] = 0.0  # Not available from account endpoint
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
    """Process portfolio data for Binance (no equity holdings — pass through)."""
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
