"""
Mapping SilverTrade AI API Request to Bybit API Parameters.

Bybit v5 order parameters (POST /v5/order/create):
    category    – "spot" | "linear" (USDT perpetual)
    symbol      – Trading pair (e.g. "BTCUSDT")
    side        – "Buy" | "Sell"
    orderType   – "Market" | "Limit" | "StopLoss" | "TakeProfit"
    qty         – Order quantity (base asset)
    price       – Order price (quote asset, for LIMIT orders)
    triggerPrice– Stop price for SL/TP orders
    timeInForce – "GTC" | "IOC" | "FOK" | "PostOnly"
    orderLinkId – Client-supplied order ID (strategy reference)
    reduceOnly  – Bool (for futures)
    positionIdx – 0=one-way, 1=buy side, 2=sell side (for futures hedge)

SilverTrade → Bybit field mapping:
    pricetype   → orderType (mapped via map_order_type)
    action      → side ("Buy" | "Sell")
    quantity    → qty
    price       → price
    trigger_price → triggerPrice
    validity    → timeInForce
    strategy    → orderLinkId

References:
  https://bybit-exchange.github.io/docs/v5/order/create-order
"""

from database.token_db import get_br_symbol, get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)


def _order_size(quantity, symbol, exchange):
    qty = float(quantity)
    info = get_symbol_info(symbol, exchange)
    if info and info.instrumenttype == "SPOT":
        return qty
    return qty


def transform_data(data, token):
    """
    Transform SilverTrade AI API request to Bybit POST /v5/order/create body.

    Bybit order body:
        {
          "category": "spot",
          "symbol": "BTCUSDT",
          "side": "Buy",
          "orderType": "Market",
          "qty": "0.001",
          "price": "67000",
          "timeInForce": "GTC"
        }
    """
    symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
    order_type = map_order_type(data["pricetype"])
    side = "Buy" if data["action"].upper() == "BUY" else "Sell"

    quantity = _order_size(data["quantity"], data["symbol"], data["exchange"])
    qty_str = f"{quantity:.8f}".rstrip("0").rstrip(".")

    body = {
        "category": "spot",
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty_str,
    }

    # Add price for LIMIT orders
    if order_type == "Limit":
        price = data.get("price", "0")
        body["price"] = f"{float(price):.8f}".rstrip("0").rstrip(".")
        body["timeInForce"] = "GTC"

    # Handle stop-loss and take-profit orders
    if order_type in ("StopLoss", "TakeProfit"):
        trigger = data.get("trigger_price", "0")
        body["triggerPrice"] = f"{float(trigger):.8f}".rstrip("0").rstrip(".")
        # For stop-limit orders, also include price
        if data["pricetype"] == "SL":
            price = data.get("price", "0")
            body["price"] = f"{float(price):.8f}".rstrip("0").rstrip(".")
            body["timeInForce"] = "GTC"

    # Handle IOC validity
    if data.get("validity") == "IOC":
        body["timeInForce"] = "IOC"

    # Client order ID (strategy reference)
    if data.get("strategy"):
        strategy = str(data["strategy"])[:30]
        body["orderLinkId"] = strategy

    # Reduce-only for futures
    if data.get("reduce_only") is True and data.get("exchange") == "CRYPTO_FUTURES":
        body["reduceOnly"] = True

    logger.debug(f"[Bybit] Transformed order: {body}")
    return body


def transform_modify_order_data(data):
    """
    Transform SilverTrade AI modify order data to Bybit POST /v5/order/amend body.

    Bybit amend fields:
        symbol      – Trading pair (required)
        orderId     – Order ID (required)
        orderLinkId – Alternative to orderId
        qty         – New quantity
        price       – New limit price (for limit orders)
        triggerPrice– New trigger price (for stop orders)
    """
    symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
    orderid = data["orderid"]

    body = {
        "category": "spot",
        "symbol": symbol,
        "orderId": str(orderid),
    }

    # Add fields that are being modified
    if data.get("quantity"):
        qty = float(data["quantity"])
        body["qty"] = f"{qty:.8f}".rstrip("0").rstrip(".")

    if data.get("price") and data["pricetype"] != "SL-M":
        price = float(data["price"])
        body["price"] = f"{price:.8f}".rstrip("0").rstrip(".")

    if data.get("trigger_price"):
        trigger = float(data["trigger_price"])
        body["triggerPrice"] = f"{trigger:.8f}".rstrip("0").rstrip(".")

    return body


def map_order_type(pricetype):
    """Map SilverTrade AI pricetype to Bybit order type."""
    mapping = {
        "MARKET": "Market",
        "LIMIT": "Limit",
        "SL": "StopLoss",
        "SL-M": "StopLoss",
        "SL-MARKET": "StopLoss",
    }
    return mapping.get(pricetype, "Market")


def map_product_type(product):
    """Map SilverTrade AI product type to Bybit equivalent."""
    return product


def reverse_map_product_type(br_product):
    """Map Bybit position type back to SilverTrade AI product type."""
    return "CNC"


def map_exchange(br_exchange):
    """Map Bybit exchange field to SilverTrade AI exchange code."""
    return "CRYPTO"


def map_exchange_type(exchange):
    """Map SilverTrade AI exchange code to Bybit context."""
    return "CRYPTO"
