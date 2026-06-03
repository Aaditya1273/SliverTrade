"""
Bybit Order Management API.

Endpoints (all POST, not POST/POST/DELETE like Binance):
  POST /v5/order/create   → Place order
  POST /v5/order/cancel   → Cancel order
  POST /v5/order/amend    → Amend/modify order
  GET  /v5/order/realtime → Get open orders
  GET  /v5/order/history  → Order history
  GET  /v5/execution/list → Trade history

References:
  https://bybit-exchange.github.io/docs/v5/order/create-order
"""

import json
import os
import threading
import time

from broker.bybit.api.baseurl import TRADE_TYPE_LINEAR, TRADE_TYPE_SPOT, get_api_response
from broker.bybit.mapping.transform_data import (
    map_order_type,
    map_product_type,
    map_exchange_type,
    transform_data,
    transform_modify_order_data,
    reverse_map_product_type,
)
from database.token_db import get_br_symbol, get_oa_symbol, get_symbol, get_token
from utils.logging import get_logger

logger = get_logger(__name__)

# --- In-memory orderId → symbol mapping for cancel (Bybit requires symbol) ---
_order_symbol_map = {}
_order_symbol_map_lock = threading.Lock()

# --- Per-Symbol Smart Order Lock ---
_symbol_locks = {}
_symbol_locks_lock = threading.Lock()


def _get_symbol_lock(symbol, exchange, product):
    key = f"{symbol}:{exchange}:{product}"
    with _symbol_locks_lock:
        if key not in _symbol_locks:
            _symbol_locks[key] = threading.Lock()
        return _symbol_locks[key]


# ---------------------------------------------------------------------------
# Order book / trade book
# ---------------------------------------------------------------------------

def get_order_book(auth):
    """Fetch open orders + recent order history."""
    try:
        all_orders = []

        # 1. Fetch open orders from realtime endpoint
        open_result = get_api_response(
            "/v5/order/realtime", auth, method="GET", signed=True
        )
        if open_result.get("success"):
            data = open_result.get("result", {})
            orders_list = data.get("list", [])
            if isinstance(orders_list, list):
                all_orders.extend(orders_list)

        # 2. Fetch recent order history
        hist_result = get_api_response(
            "/v5/order/history", auth, method="GET", signed=True,
            params={"limit": 50}
        )
        if hist_result.get("success"):
            data = hist_result.get("result", {})
            hist_list = data.get("list", [])
            if isinstance(hist_list, list):
                # Merge with dedup, preferring history for authoritative status
                hist_by_id = {o.get("orderId"): o for o in hist_list if isinstance(o, dict)}
                all_orders = [
                    o for o in all_orders
                    if not (isinstance(o, dict) and o.get("orderId") in hist_by_id)
                ]
                all_orders.extend(hist_list)

        logger.debug(f"[Bybit] get_order_book: {len(all_orders)} orders")
        return all_orders

    except Exception as e:
        logger.error(f"[Bybit] Exception in get_order_book: {e}")
        return []


def get_trade_book(auth):
    """Fetch trade fills/execution history."""
    try:
        result = get_api_response(
            "/v5/execution/list", auth, method="GET", signed=True,
            params={"limit": 100}
        )
        if result.get("success"):
            data = result.get("result", {})
            trades = data.get("list", [])
            return trades if isinstance(trades, list) else []
        return []
    except Exception as e:
        logger.error(f"[Bybit] Exception in get_trade_book: {e}")
        return []


# ---------------------------------------------------------------------------
# Positions / holdings
# ---------------------------------------------------------------------------

def get_positions(auth):
    """Fetch account wallet balances as synthetic position dicts."""
    positions = []

    try:
        result = get_api_response(
            "/v5/account/wallet-balance", auth, method="GET",
            signed=True, params={"accountType": "UNIFIED"}
        )
        if not result.get("success"):
            logger.warning(f"[Bybit] get_positions failed: {result}")
            return positions

        data = result.get("result", {})
        coin_list = []

        # Bybit wallet-balance returns accounts in 'list'
        accounts = data.get("list", [])
        for acct in accounts:
            if isinstance(acct, dict):
                coins = acct.get("coin", [])
                if isinstance(coins, list):
                    for coin in coins:
                        if isinstance(coin, dict):
                            coin_list.append(coin)

        for coin in coin_list:
            asset = coin.get("coin", "")
            total_str = coin.get("walletBalance", "0")
            free_str = coin.get("free", "0")
            locked_str = coin.get("locked", "0")

            total = float(total_str)
            if total <= 0:
                continue

            positions.append({
                "symbol": asset,
                "asset": asset,
                "free": float(free_str),
                "locked": float(locked_str),
                "total": total,
                "product_symbol": f"{asset}USDT",
                "_is_spot": True,
            })

        logger.debug(f"[Bybit] get_positions: {len(positions)} non-zero assets")
        return positions

    except Exception as e:
        logger.error(f"[Bybit] Exception in get_positions: {e}")
        return positions


def get_holdings(auth):
    """Bybit has no equity holdings concept."""
    return []


def get_open_position(tradingsymbol, exchange, product, auth):
    """Return the net position size (as string) for a given symbol."""
    br_symbol = get_br_symbol(tradingsymbol, exchange) or tradingsymbol
    positions = get_positions(auth)

    for pos in positions:
        if pos.get("product_symbol") == br_symbol:
            return str(pos.get("total", 0))
    return "0"


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------

def place_order_api(data, auth):
    """
    Place a new order on Bybit via POST /v5/order/create.

    Returns:
        (response_shim, response_dict, orderid)
    """
    token = get_token(data["symbol"], data["exchange"])
    logger.info(f"[Bybit] place_order: symbol={data['symbol']} token={token}")

    if not token:
        msg = (f"[Bybit] Symbol '{data['symbol']}' not found in master contract DB "
               f"for exchange '{data['exchange']}'. Run master contract sync first.")
        logger.error(msg)
        class _ErrResp:
            status_code = 400
            status = 400
        return _ErrResp(), {"status": "error", "message": msg}, None

    # Transform SilverTrade data → Bybit API params
    order_body = transform_data(data, token)
    
    # Bybit order endpoints use category parameter; map exchange to category
    category = data.get("category", TRADE_TYPE_SPOT)

    result = get_api_response(
        "/v5/order/create", auth, method="POST",
        body=order_body, signed=True, category=category
    )
    logger.debug(f"[Bybit] place_order response: {result}")

    order_id = None
    if result.get("success"):
        order_data = result.get("result", {})
        order_id = str(order_data.get("orderId", ""))
        # Store orderId → symbol mapping for cancellation
        br_symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
        with _order_symbol_map_lock:
            _order_symbol_map[order_id] = br_symbol
        logger.info(f"[Bybit] Order placed. orderId={order_id} symbol={br_symbol}")
        response_dict = {"orderid": order_id, "status": "success"}
    else:
        error = result.get("error", {})
        msg = error.get("message") or error.get("code") or str(error)
        logger.error(f"[Bybit] Order placement failed: {msg}")
        response_dict = {"status": "error", "message": msg}

    class _Resp:
        status_code = 200 if result.get("success") else 400
        status = status_code

    return _Resp(), response_dict, order_id


def place_bracket_order_api(data, auth):
    """Bybit supports conditional orders via orderLinkId; use place_order_api."""
    # For now, fall back to place_order_api
    return place_order_api(data, auth)


def place_smartorder_api(data, auth):
    """Smart order: adjusts position to reach the desired position_size."""
    res = None
    symbol = data.get("symbol")
    exchange = data.get("exchange")
    product = data.get("product")

    symbol_lock = _get_symbol_lock(symbol, exchange, product)

    with symbol_lock:
        position_size = float(data.get("position_size", "0"))
        current_position = float(
            get_open_position(symbol, exchange, map_product_type(product), auth)
        )
        logger.info(f"[Bybit] SmartOrder: target={position_size} current={current_position}")

        if position_size == 0 and current_position == 0 and float(data["quantity"]) != 0:
            return place_order_api(data, auth)

        if position_size == current_position:
            msg = ("No OpenPosition Found. Not placing Exit order."
                   if float(data["quantity"]) == 0
                   else "No action needed. Position size matches current position")
            return res, {"status": "success", "message": msg}, None

        action = None
        quantity = 0

        if position_size == 0 and current_position > 0:
            action, quantity = "SELL", abs(current_position)
        elif position_size == 0 and current_position < 0:
            action, quantity = "BUY", abs(current_position)
        elif current_position == 0:
            action = "BUY" if position_size > 0 else "SELL"
            quantity = abs(position_size)
        elif position_size > current_position:
            action, quantity = "BUY", position_size - current_position
        elif position_size < current_position:
            action, quantity = "SELL", current_position - position_size

        if action:
            order_data = data.copy()
            order_data["action"] = action
            order_data["quantity"] = str(quantity)
            return place_order_api(order_data, auth)

    return res, {"status": "success", "message": "No action needed"}, None


# ---------------------------------------------------------------------------
# Order cancellation
# ---------------------------------------------------------------------------

def cancel_order(orderid, auth):
    """
    Cancel an open order via POST /v5/order/cancel.

    Bybit requires the 'symbol' parameter alongside 'orderId' for cancellation.
    Uses an in-memory _order_symbol_map populated when orders are placed.
    Falls back to fetching from open orders if not in local map.
    """
    try:
        orderid_str = str(orderid)

        # Look up symbol from in-memory map
        with _order_symbol_map_lock:
            symbol = _order_symbol_map.get(orderid_str)

        # Fallback: fetch from open orders
        if not symbol:
            logger.warning(f"[Bybit] Symbol for order {orderid} not in local map; fetching from API")
            open_result = get_api_response(
                "/v5/order/realtime", auth, method="GET", signed=True
            )
            if open_result.get("success"):
                data = open_result.get("result", {})
                for order in data.get("list", []):
                    if isinstance(order, dict) and order.get("orderId") == orderid_str:
                        symbol = order.get("symbol", "")
                        break

        if not symbol:
            return {"status": "error", "message": "Could not determine symbol for order cancellation."}, 400

        body = {"symbol": symbol, "orderId": orderid_str}
        result = get_api_response(
            "/v5/order/cancel", auth, method="POST",
            body=body, signed=True
        )

        if result.get("success"):
            logger.info(f"[Bybit] Order {orderid} cancelled (symbol={symbol})")
            with _order_symbol_map_lock:
                _order_symbol_map.pop(orderid_str, None)
            return {"status": "success", "orderid": orderid}, 200
        else:
            error = result.get("error", {})
            msg = error.get("message") or str(error)
            return {"status": "error", "message": msg}, 400

    except Exception as e:
        logger.error(f"[Bybit] Cancel error: {e}")
        return {"status": "error", "message": str(e)}, 400


def cancel_all_orders_api(data, auth):
    """Cancel all open orders. Bybit supports POST /v5/order/cancel-all."""
    try:
        result = get_api_response(
            "/v5/order/cancel-all", auth, method="POST",
            body={"category": "spot"}, signed=True
        )
        if result.get("success"):
            logger.info("[Bybit] All orders cancelled")
            return ["all"], []
        return [], []
    except Exception as e:
        logger.error(f"[Bybit] cancel_all error: {e}")
        return [], []


# ---------------------------------------------------------------------------
# Order modification (amend)
# ---------------------------------------------------------------------------

def modify_order(data, auth):
    """
    Modify an existing open order via POST /v5/order/amend.

    Bybit supports amending orders natively (unlike Binance which requires cancel+replace).
    """
    orderid = data["orderid"]
    transformed = transform_modify_order_data(data)

    result = get_api_response(
        "/v5/order/amend", auth, method="POST",
        body=transformed, signed=True
    )

    if result.get("success"):
        return {"status": "success", "orderid": orderid}, 200
    else:
        error = result.get("error", {})
        msg = error.get("message") or str(error)
        return {"status": "error", "message": msg}, 400


# ---------------------------------------------------------------------------
# Close all positions
# ---------------------------------------------------------------------------

def close_all_positions(current_api_key, auth):
    """Close all open positions using market orders."""
    positions = get_positions(auth)
    if not positions:
        return {"message": "No Open Positions Found"}, 200

    for pos in positions:
        try:
            total = float(pos.get("total", 0))
            if total <= 0:
                continue

            asset = pos.get("asset", "")
            action = "SELL"
            quantity = str(total)

            logger.info(f"[Bybit] Close: {action} {quantity} {asset}")

            order_payload = {
                "apikey": current_api_key,
                "strategy": "Squareoff",
                "symbol": asset + "USDT",
                "action": action,
                "exchange": "CRYPTO",
                "pricetype": "MARKET",
                "product": "CNC",
                "quantity": quantity,
            }
            _, api_response, _ = place_order_api(order_payload, auth)
            logger.debug(f"[Bybit] Close response: {api_response}")

        except Exception as e:
            logger.error(f"[Bybit] Error closing position for {pos.get('asset', '')}: {e}")

    return {"status": "success", "message": "All Open Positions SquaredOff"}, 200
