"""
SilverTrade AI — Trailing Stop Loss Monitor
===========================================
Background job that updates trailing stop loss orders as price moves favourably.
"""

import logging
import os
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

STRATEGY_HOST = os.getenv("STRATEGY_HOST", "http://127.0.0.1:5007")
PLATFORM_HOST = os.getenv("HOST_SERVER", "http://127.0.0.1:5000")


def get_atr(symbol: str, exchange: str) -> float:
    """Get Average True Range for a symbol."""
    try:
        response = requests.get(
            f"{STRATEGY_HOST}/api/v1/atr",
            params={"symbol": symbol, "exchange": exchange},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("atr", 0)
    except Exception as e:
        logger.error(f"Failed to get ATR for {symbol}: {e}")
    return 0


def get_open_positions(api_key: str) -> list:
    """Get user's open positions."""
    try:
        response = requests.post(
            f"{PLATFORM_HOST}/api/v1/positions",
            json={"apikey": api_key},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("positions", [])
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
    return []


def modify_sl_order(api_key: str, order_id: str, new_trigger_price: float) -> bool:
    """Modify an existing stop loss order."""
    try:
        response = requests.post(
            f"{PLATFORM_HOST}/api/v1/modifyorder",
            json={
                "apikey": api_key,
                "orderid": order_id,
                "variety": "NORMAL",
                "trigger_price": str(new_trigger_price),
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to modify SL order {order_id}: {e}")
    return False


def run_trailing_sl_monitor(api_key: str) -> None:
    """Run trailing SL check for all open positions."""
    positions = get_open_positions(api_key)
    
    for position in positions:
        symbol = position.get("symbol", "")
        exchange = position.get("exchange", "NSE")
        ltp = float(position.get("ltp", 0))
        entry_price = float(position.get("average_price", 0))
        
        if not symbol or ltp <= 0 or entry_price <= 0:
            continue
        
        # Get ATR for trailing calculation
        atr = get_atr(symbol, exchange)
        if atr <= 0:
            continue
        
        # Check if price has moved favourably (up for LONG, down for SHORT)
        # For LONG positions: if LTP > entry + ATR, move SL up
        # For SHORT positions: if LTP < entry - ATR, move SL down
        
        action = position.get("action", "BUY")
        
        if action == "BUY":
            # LONG position
            if ltp > entry_price + atr:
                # Move SL up by ATR * 0.5
                new_sl = ltp - (atr * 1.5)
                logger.info(f"Trailing SL for {symbol}: LTP {ltp}, new SL {new_sl}")
                # TODO: Find and modify the SL order for this position
        elif action == "SELL":
            # SHORT position
            if ltp < entry_price - atr:
                # Move SL down by ATR * 0.5
                new_sl = ltp + (atr * 1.5)
                logger.info(f"Trailing SL for {symbol}: LTP {ltp}, new SL {new_sl}")
                # TODO: Find and modify the SL order for this position


def auto_place_sl_tp(api_key: str, symbol: str, exchange: str, action: str, 
                     quantity: str, entry_price: float, order_id: str) -> None:
    """Automatically place SL and TP orders after entry fills."""
    try:
        atr = get_atr(symbol, exchange)
        if atr <= 0:
            logger.warning(f"Cannot auto-place SL/TP: ATR not available for {symbol}")
            return
        
        # Calculate SL and TP prices
        if action == "BUY":
            sl_price = entry_price - (atr * 1.5)
            tp_price = entry_price + (atr * 2.5)
            sl_action = "SELL"
            tp_action = "SELL"
        else:  # SELL
            sl_price = entry_price + (atr * 1.5)
            tp_price = entry_price - (atr * 2.5)
            sl_action = "BUY"
            tp_action = "BUY"
        
        logger.info(f"Auto-placing SL/TP for {symbol}: SL={sl_price}, TP={tp_price}")
        
        # Place SL order (SL-M)
        sl_order_data = {
            "symbol": symbol,
            "exchange": exchange,
            "action": sl_action,
            "product_type": "MIS",
            "pricetype": "SL-M",
            "quantity": quantity,
            "price": "0",
            "trigger_price": str(sl_price),
            "tag": f"SL_{order_id}",
        }
        
        # Place TP order (LIMIT)
        tp_order_data = {
            "symbol": symbol,
            "exchange": exchange,
            "action": tp_action,
            "product_type": "MIS",
            "pricetype": "LIMIT",
            "quantity": quantity,
            "price": str(tp_price),
            "trigger_price": "0",
            "tag": f"TP_{order_id}",
        }
        
        # TODO: Call place_order service for both orders
        logger.info(f"SL/TP orders prepared for {symbol}")
        
    except Exception as e:
        logger.error(f"Failed to auto-place SL/TP: {e}")
