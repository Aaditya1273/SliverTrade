"""
Binance Order Management API.

Endpoints:
  POST   /api/v3/order           → Place order
  DELETE /api/v3/order           → Cancel order
  GET    /api/v3/openOrders      → Get open orders
  GET    /api/v3/allOrders       → Order history
  GET    /api/v3/myTrades        → Trade history
  GET    /api/v3/account         → Account info for positions

References:
  https://binance-docs.github.io/apidocs/spot/en/#trade-listing
"""

import json
import os
import threading
import time

from broker.binance.api.baseurl import TRADE_TYPE_FUTURES, TRADE_TYPE_SPOT, get_api_response
from broker.binance.mapping.transform_data import (
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


# --- In-memory orderId → symbol mapping for cancel (Binance requires symbol) ---
_order_symbol_map = {}  # {orderId_str: symbol}
_order_symbol_map_lock = threading.Lock()

# --- Per-Symbol Smart Order Lock ---
_symbol_locks = {}
_symbol_locks_lock = threading.Lock()


def _get_symbol_lock(symbol, exchange, product):
    """Get or create a per-symbol lock for serializing smart orders."""
    key = f"{symbol}:{exchange}:{product}"
    with _symbol_locks_lock:
        if key not in _symbol_locks:
            _symbol_locks[key] = threading.Lock()
        return _symbol_locks[key]


# ---------------------------------------------------------------------------
# Order book / trade book
# ---------------------------------------------------------------------------


def get_order_book(auth):
    """Fetch all recent orders (open + recent history) for the account.

    Binance open orders endpoint returns only currently-open orders.
    To show a complete order book view (matching the Delta Exchange pattern),
    we also fetch recent order history from /api/v3/allOrders.
    """
    try:
        all_orders = []

        # 1. Fetch open orders
        open_result = get_api_response("/api/v3/openOrders", auth, method="GET", signed=True)
        if open_result.get("success"):
            all_orders.extend(open_result.get("result", []))

        # 2. Fetch recent order history (last 50 orders)
        from datetime import datetime, timezone

        one_day_ago = int((datetime.now(timezone.utc).timestamp() - 86400) * 1000)

        hist_result = get_api_response(
            "/api/v3/allOrders",
            auth,
            method="GET",
            signed=True,
            params={"limit": 50, "startTime": one_day_ago},
        )
        if hist_result.get("success"):
            # Merge, preferring allOrders entries (authoritative final status)
            # since openOrders may still show "NEW" for orders that have since filled.
            hist_orders = hist_result.get("result", [])
            hist_by_id = {o.get("orderId"): o for o in hist_orders if isinstance(o, dict)}
            # Remove open orders that also appear in history, then add history versions
            all_orders = [
                o
                for o in all_orders
                if not (isinstance(o, dict) and o.get("orderId") in hist_by_id)
            ]
            all_orders.extend(hist_orders)

        logger.debug(f"[Binance] get_order_book: {len(all_orders)} orders (open + history)")
        return all_orders

    except Exception as e:
        logger.error(f"[Binance] Exception in get_order_book: {e}")
        return []


def get_trade_book(auth):
    """Fetch today's filled trades (fills)."""
    try:
        result = get_api_response(
            "/api/v3/myTrades", auth, method="GET", signed=True, params={"limit": 500}
        )
        if result.get("success"):
            return result.get("result", [])
        return []
    except Exception as e:
        logger.error(f"[Binance] Exception in get_trade_book: {e}")
        return []


# ---------------------------------------------------------------------------
# Positions / holdings
# ---------------------------------------------------------------------------


def get_positions(auth):
    """
    Fetch account balances from Binance Spot wallet and futures positions.

    Spot positions:
        GET /api/v3/account → balances[] (free + locked per asset)

    USD-M Futures positions:
        GET /fapi/v2/account → positions[] (size, entry, PnL, leverage)

    Only returns non-zero positions (both spot and futures).
    """
    positions = []

    try:
        # ── 1. Fetch spot account balances ──────────────────────────────────────
        result = get_api_response("/api/v3/account", auth, method="GET", signed=True)
        if result.get("success"):
            data = result.get("result", {})
            balances = data.get("balances", [])

            for balance in balances:
                asset = balance.get("asset", "")
                free = float(balance.get("free", 0))
                locked = float(balance.get("locked", 0))
                total = free + locked
                if total <= 0:
                    continue

                positions.append(
                    {
                        "symbol": asset,
                        "asset": asset,
                        "free": free,
                        "locked": locked,
                        "total": total,
                        "product_symbol": f"{asset}USDT",
                        "_is_spot": True,
                    }
                )
        else:
            logger.warning(f"[Binance] Spot account fetch failed: {result.get('error')}")

        # ── 2. Fetch USD-M futures positions ──────────────────────────────────
        try:
            futures_result = get_api_response(
                "/fapi/v2/account",
                auth,
                method="GET",
                signed=True,
                trade_type=TRADE_TYPE_FUTURES,
            )
            if futures_result.get("success"):
                futures_data = futures_result.get("result", {})
                fut_positions = futures_data.get("positions", [])

                for pos in fut_positions:
                    if not isinstance(pos, dict):
                        continue

                    size = float(pos.get("positionAmt", 0))
                    if size == 0:
                        continue

                    symbol = pos.get("symbol", "")
                    entry_price = float(pos.get("entryPrice", 0))
                    unrealized_pnl = float(pos.get("unrealizedProfit", 0))
                    leverage = int(float(pos.get("leverage", 1)))
                    liquidation_price = float(pos.get("liquidationPrice", 0))

                    positions.append(
                        {
                            "symbol": symbol,
                            "asset": symbol.replace("USDT", "").replace("BUSD", ""),
                            "product_symbol": symbol,
                            "size": size,
                            "entry_price": entry_price,
                            "unrealized_pnl": unrealized_pnl,
                            "leverage": leverage,
                            "liquidation_price": liquidation_price,
                            "_is_futures": True,
                        }
                    )

                logger.debug(
                    f"[Binance] Futures positions: {len(fut_positions)} raw, "
                    f"{sum(1 for p in fut_positions if isinstance(p, dict) and float(p.get('positionAmt', 0)) != 0)} non-zero"
                )
            else:
                logger.debug(
                    f"[Binance] Futures account fetch skipped or failed: {futures_result.get('error')}"
                )
        except Exception as fut_err:
            logger.debug(
                f"[Binance] Futures position fetch optional (may not be enabled): {fut_err}"
            )

        logger.debug(f"[Binance] get_positions: {len(positions)} total (spot + futures)")
        return positions

    except Exception as e:
        logger.error(f"[Binance] Exception in get_positions: {e}")
        return positions


def get_holdings(auth):
    """Binance has no equity holdings concept; spot balances shown in positions."""
    return []


def get_open_position(tradingsymbol, exchange, product, auth):
    """
    Return the net position size (as string) for a given symbol.
    Positive = long, negative = short, "0" = flat.
    """
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
    Place a new order on Binance via POST /api/v3/order.

    Returns:
        (response_shim, response_dict, orderid)
    """
    token = get_token(data["symbol"], data["exchange"])
    logger.info(f"[Binance] place_order: symbol={data['symbol']} token={token}")

    if not token:
        msg = (
            f"[Binance] Symbol '{data['symbol']}' not found in master contract DB "
            f"for exchange '{data['exchange']}'. Run master contract sync first."
        )
        logger.error(msg)

        class _ErrResp:
            status_code = 400
            status = 400

        return _ErrResp(), {"status": "error", "message": msg}, None

    # Transform SilverTrade data → Binance API params
    order_params = transform_data(data, token)

    # Determine trade type based on exchange
    trade_type = TRADE_TYPE_FUTURES if data.get("exchange") == "CRYPTO_FUTURES" else TRADE_TYPE_SPOT

    # Set endpoint based on trade type
    endpoint = "/api/v3/order"
    if trade_type == TRADE_TYPE_FUTURES:
        endpoint = "/fapi/v1/order"

    result = get_api_response(
        endpoint, auth, method="POST", params=order_params, signed=True, trade_type=trade_type
    )
    logger.debug(f"[Binance] place_order response: {result}")

    order_id = None
    if result.get("success"):
        order_data = result.get("result", {})
        order_id = str(order_data.get("orderId", ""))
        # Store orderId → symbol mapping for cancellation (Binance requires symbol)
        br_symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
        with _order_symbol_map_lock:
            _order_symbol_map[order_id] = br_symbol
        logger.info(f"[Binance] Order placed. orderId={order_id} symbol={br_symbol}")
        response_dict = {"orderid": order_id, "status": "success"}
    else:
        error = result.get("error", {})
        msg = error.get("message") or error.get("code") or str(error)
        logger.error(f"[Binance] Order placement failed: {msg}")
        response_dict = {"status": "error", "message": msg}

    class _Resp:
        status_code = 200 if result.get("success") else 400
        status = status_code

    return _Resp(), response_dict, order_id


def place_bracket_order_api(data, auth):
    """Place a bracket order (OCO - One Cancels Other) on Binance."""
    # Binance supports OCO via POST /api/v3/order/oco
    token = get_token(data["symbol"], data["exchange"])

    if not token:

        class _ErrResp:
            status_code = 400
            status = 400

        return (
            _ErrResp(),
            {"status": "error", "message": "Symbol not found in master contract DB"},
            None,
        )

    has_stop_loss = data.get("bracket_stop_loss_price") is not None
    has_take_profit = data.get("bracket_take_profit_price") is not None

    if not has_stop_loss or not has_take_profit:
        # Fall back to regular order + separate stop loss
        logger.warning("[Binance] bracket_order needs both SL and TP; falling back to place_order")
        return place_order_api(data, auth)

    # Build OCO parameters
    symbol = get_br_symbol(data["symbol"], data["exchange"]) or data["symbol"]
    side = data["action"].upper()
    quantity = data["quantity"]

    # Main limit order
    price = data.get("price", "0")

    # Stop-limit leg
    stop_price = data.get("bracket_stop_loss_price", "0")
    stop_limit_price = data.get("bracket_stop_loss_limit_price", stop_price)

    # Take-profit limit leg
    tp_price = data.get("bracket_take_profit_price", "0")

    oco_params = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "stopPrice": stop_price,
        "stopLimitPrice": stop_limit_price,
        "stopLimitTimeInForce": "GTC",
    }

    result = get_api_response(
        "/api/v3/order/oco", auth, method="POST", params=oco_params, signed=True
    )

    order_id = None
    if result.get("success"):
        order_data = result.get("result", {})
        order_id = str(order_data.get("orderListId", ""))
        response_dict = {"orderid": order_id, "status": "success"}
    else:
        error = result.get("error", {})
        msg = error.get("message") or error.get("code") or str(error)
        response_dict = {"status": "error", "message": msg}

    class _Resp:
        status_code = 200 if result.get("success") else 400
        status = status_code

    return _Resp(), response_dict, order_id


def place_smartorder_api(data, auth):
    """
    Smart order: adjusts position to reach the desired position_size.
    """
    res = None
    symbol = data.get("symbol")
    exchange = data.get("exchange")
    product = data.get("product")

    # Per-symbol lock
    symbol_lock = _get_symbol_lock(symbol, exchange, product)

    with symbol_lock:
        position_size = float(data.get("position_size", "0"))
        current_position = float(
            get_open_position(symbol, exchange, map_product_type(product), auth)
        )
        logger.info(f"[Binance] SmartOrder: target={position_size} current={current_position}")

        if position_size == 0 and current_position == 0 and float(data["quantity"]) != 0:
            result = place_order_api(data, auth)
            return result

        if position_size == current_position:
            msg = (
                "No OpenPosition Found. Not placing Exit order."
                if float(data["quantity"]) == 0
                else "No action needed. Position size matches current position"
            )
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
    """Cancel an open order via DELETE /api/v3/order.

    Binance requires the 'symbol' parameter alongside 'orderId' for cancellation.
    Since the cancel_order_service only passes (orderid, auth), we maintain an
    in-memory _order_symbol_map that is populated when orders are placed.

    If the symbol is not found in the local map (e.g. after restart), we make
    an extra GET /api/v3/openOrders call to discover it.
    """
    try:
        orderid_str = str(orderid)

        # Look up symbol from in-memory map
        with _order_symbol_map_lock:
            symbol = _order_symbol_map.get(orderid_str)

        # Fallback: fetch from open orders if not in local map
        if not symbol:
            logger.warning(
                f"[Binance] Symbol for order {orderid} not in local map; fetching from API"
            )
            open_orders_result = get_api_response(
                "/api/v3/openOrders", auth, method="GET", signed=True
            )
            if open_orders_result.get("success"):
                for order in open_orders_result.get("result", []):
                    if str(order.get("orderId")) == orderid_str:
                        symbol = order.get("symbol", "")
                        break

        if not symbol:
            return {
                "status": "error",
                "message": "Could not determine symbol for order cancellation. Order may already be filled or cancelled.",
            }, 400

        params = {"symbol": symbol, "orderId": int(orderid_str)}
        result = get_api_response(
            "/api/v3/order", auth, method="DELETE", params=params, signed=True
        )

        if result.get("success"):
            logger.info(f"[Binance] Order {orderid} cancelled (symbol={symbol})")
            # Clean up from local map
            with _order_symbol_map_lock:
                _order_symbol_map.pop(orderid_str, None)
            return {"status": "success", "orderid": orderid}, 200
        else:
            error = result.get("error", {})
            msg = error.get("message") or str(error)
            return {"status": "error", "message": msg}, 400

    except Exception as e:
        logger.error(f"[Binance] Cancel error: {e}")
        return {"status": "error", "message": str(e)}, 400


def cancel_all_orders_api(data, auth):
    """Cancel all currently open orders."""
    try:
        # Binance supports DELETE /api/v3/openOrders to cancel all
        result = get_api_response("/api/v3/openOrders", auth, method="DELETE", signed=True)
        if result.get("success"):
            cancelled = result.get("result", [])
            logger.info(f"[Binance] Cancelled {len(cancelled)} open orders")
            return [str(o.get("orderId", "")) for o in cancelled], []
        return [], []

    except Exception as e:
        logger.error(f"[Binance] cancel_all error: {e}")
        return [], []


# ---------------------------------------------------------------------------
# Order modification
# ---------------------------------------------------------------------------


def modify_order(data, auth):
    """
    Modify an existing open order.
    Binance does NOT support order modification. The order must be cancelled
    and re-placed. We simulate this atomically.
    """
    orderid = data["orderid"]

    # Cancel the existing order
    cancel_result, status = cancel_order(orderid, auth)
    if status != 200:
        return cancel_result, status

    # Place a new order with modified parameters
    result, response_dict, new_order_id = place_order_api(data, auth)
    if new_order_id:
        return {"status": "success", "orderid": new_order_id}, 200
    return response_dict, 400


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

            logger.info(f"[Binance] Close: {action} {quantity} {asset}")

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
            logger.debug(f"[Binance] Close response: {api_response}")

        except Exception as e:
            logger.error(f"[Binance] Error closing position for {pos.get('asset', '')}: {e}")

    return {"status": "success", "message": "All Open Positions SquaredOff"}, 200
