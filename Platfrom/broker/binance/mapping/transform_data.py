"""
Mapping SilverTrade AI API Request to Binance API Parameters.

References:
  https://binance-docs.github.io/apidocs/spot/en/#new-order-trade
"""

from database.token_db import get_br_symbol, get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)


def _order_size(quantity, symbol, exchange):
    """Convert quantity to float (Binance uses string for precision)."""
    qty = float(quantity)
    info = get_symbol_info(symbol, exchange)
    if info and info.instrumenttype == "SPOT":
        return qty
    return qty


def transform_data(data, token):
    """
    Transform SilverTrade AI API request to Binance POST /api/v3/order params.

    Binance order parameters (spot):
        symbol        - Trading pair (e.g. "BTCUSDT")
        side          - "BUY" or "SELL"
        type          - "MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_LIMIT",
                        "TAKE_PROFIT", "TAKE_PROFIT_LIMIT", "LIMIT_MAKER"
        timeInForce   - "GTC", "IOC", "FOK"
        quantity      - Order quantity (base asset)
        price         - Order price (quote asset)
        stopPrice     - Stop price for stop-loss/take-profit orders

    SilverTrade AI → Binance field mapping:
        pricetype   →  type (mapped via map_order_type)
        action      →  side (uppercased)
        quantity    →  quantity
        price       →  price (string for LIMIT orders)
        trigger_price → stopPrice (for SL/SL-M orders)
    """
    symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
    order_type = map_order_type(data["pricetype"])
    side = data["action"].upper()

    quantity = _order_size(data["quantity"], data["symbol"], data["exchange"])
    qty_str = f"{quantity:.8f}".rstrip("0").rstrip(".")

    transformed = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": qty_str,
    }

    # Add timeInForce for LIMIT orders
    if order_type == "LIMIT":
        transformed["timeInForce"] = "GTC"
        price = data.get("price", "0")
        transformed["price"] = f"{float(price):.8f}".rstrip("0").rstrip(".")

    # Handle stop-loss and take-profit orders
    if order_type in ("STOP_LOSS", "STOP_LOSS_LIMIT"):
        trigger = data.get("trigger_price", "0")
        transformed["stopPrice"] = f"{float(trigger):.8f}".rstrip("0").rstrip(".")
        if order_type == "STOP_LOSS_LIMIT":
            transformed["timeInForce"] = "GTC"
            price = data.get("price", "0")
            transformed["price"] = f"{float(price):.8f}".rstrip("0").rstrip(".")

    if order_type in ("TAKE_PROFIT", "TAKE_PROFIT_LIMIT"):
        trigger = data.get("trigger_price", "0")
        transformed["stopPrice"] = f"{float(trigger):.8f}".rstrip("0").rstrip(".")

    # Handle IOC validity
    if data.get("validity") == "IOC":
        transformed["timeInForce"] = "IOC"

    # New client order ID (strategy reference)
    if data.get("strategy"):
        # Binance supports newClientOrderId up to 36 chars
        strategy = str(data["strategy"])[:30]
        transformed["newClientOrderId"] = strategy

    # Reduce-only flag — Binance uses reduceOnly for futures
    if data.get("reduce_only") is True and data.get("exchange") == "CRYPTO_FUTURES":
        transformed["reduceOnly"] = True

    logger.debug(f"[Binance] Transformed order: {transformed}")
    return transformed


def transform_modify_order_data(data):
    """
    Transform SilverTrade AI modify order data to Binance cancel + replace.
    Binance does not support modification — returns params for cancel + place.
    """
    return data


def map_order_type(pricetype):
    """Map SilverTrade AI pricetype to Binance order type."""
    mapping = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "SL": "STOP_LOSS_LIMIT",
        "SL-M": "STOP_LOSS",
        "SL-MARKET": "STOP_LOSS",
    }
    return mapping.get(pricetype, "MARKET")


def map_product_type(product):
    """Map SilverTrade AI product type to Binance equivalent."""
    # Binance doesn't use CNC/NRML/MIS — return as-is
    return product


def reverse_map_product_type(br_product):
    """Map Binance position type back to SilverTrade AI product type."""
    return "CNC"


def map_exchange(br_exchange):
    """Map Binance exchange field to SilverTrade AI exchange code."""
    return "CRYPTO"


def map_exchange_type(exchange):
    """Map SilverTrade AI exchange code to Binance context."""
    return "CRYPTO"
