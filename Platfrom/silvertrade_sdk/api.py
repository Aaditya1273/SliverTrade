"""
SilverTrade AI SDK - API Client
================================
Provides the same interface as the `openalgo` PyPI package's `api` class.

This module allows the platform to function without the external `openalgo`
PyPI dependency by routing SDK calls through the platform's own REST API
endpoints internally.
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

import httpx
import pandas as pd


class api:
    """
    SilverTrade AI API Client

    Drop-in replacement for `openalgo.api` from the openalgo PyPI package.
    All method signatures and return types are identical.

    Args:
        api_key: SilverTrade AI API key
        host: SilverTrade AI server URL (default: http://127.0.0.1:5000)
        version: API version (default: v1)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        version: str = "v1",
    ):
        self.api_key = api_key or os.getenv("SILVERTRADE_API_KEY", "")
        self.host = (host or os.getenv("SILVERTRADE_HOST", "http://127.0.0.1:5000")).rstrip("/")
        self.version = version
        self.base_url = f"{self.host}/api/{self.version}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    def _payload(self, **kwargs) -> Dict[str, Any]:
        payload = {"apikey": self.api_key}
        payload.update({k: v for k, v in kwargs.items() if v is not None})
        return payload

    def _post(self, endpoint: str, **kwargs) -> Any:
        """Make a POST request to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        payload = self._payload(**kwargs)
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload, headers=self._headers())
            return response.json()

    # ------------------------------------------------------------------ #
    # Order Management
    # ------------------------------------------------------------------ #

    def placeorder(
        self,
        strategy: str,
        symbol: str,
        action: str,
        exchange: str,
        price_type: str,
        product: str,
        quantity: int,
        price: float = 0,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
    ) -> Dict[str, Any]:
        """Place a new order."""
        return self._post(
            "placeorder",
            strategy=strategy,
            symbol=symbol,
            action=action,
            exchange=exchange,
            pricetype=price_type,
            product=product,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
        )

    def placesmartorder(
        self,
        strategy: str,
        symbol: str,
        action: str,
        exchange: str,
        price_type: str,
        product: str,
        quantity: int,
        position_size: int,
        price: float = 0,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
    ) -> Dict[str, Any]:
        """Place a smart order that considers current position size."""
        return self._post(
            "placesmartorder",
            strategy=strategy,
            symbol=symbol,
            action=action,
            exchange=exchange,
            pricetype=price_type,
            product=product,
            quantity=quantity,
            position_size=position_size,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
        )

    def basketorder(self, strategy: str, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Place a basket of orders."""
        return self._post("basketorder", strategy=strategy, orders=orders)

    def splitorder(
        self,
        strategy: str,
        symbol: str,
        exchange: str,
        action: str,
        quantity: int,
        splitsize: int,
        price_type: str,
        product: str,
        price: float = 0,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
    ) -> Dict[str, Any]:
        """Place a split order (large order broken into chunks)."""
        return self._post(
            "splitorder",
            strategy=strategy,
            symbol=symbol,
            exchange=exchange,
            action=action,
            quantity=quantity,
            splitsize=splitsize,
            pricetype=price_type,
            product=product,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
        )

    def optionsorder(
        self,
        strategy: str,
        underlying: str,
        exchange: str,
        offset: str,
        option_type: str,
        action: str,
        quantity: int,
        price_type: str = "MARKET",
        product: str = "MIS",
        expiry_date: Optional[str] = None,
        price: float = 0,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
    ) -> Dict[str, Any]:
        """Place an options order."""
        return self._post(
            "optionsorder",
            strategy=strategy,
            underlying=underlying,
            exchange=exchange,
            offset=offset,
            option_type=option_type,
            action=action,
            quantity=quantity,
            pricetype=price_type,
            product=product,
            expiry_date=expiry_date,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
        )

    def optionsmultiorder(
        self,
        strategy: str,
        underlying: str,
        exchange: str,
        legs: List[Dict[str, Any]],
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Place a multi-leg options order."""
        return self._post(
            "optionsmultiorder",
            strategy=strategy,
            underlying=underlying,
            exchange=exchange,
            legs=legs,
            expiry_date=expiry_date,
        )

    def modifyorder(
        self,
        order_id: str,
        strategy: str,
        symbol: str,
        action: str,
        exchange: str,
        price_type: str,
        product: str,
        quantity: int,
        price: float,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
    ) -> Dict[str, Any]:
        """Modify an existing order."""
        return self._post(
            "modifyorder",
            order_id=order_id,
            strategy=strategy,
            symbol=symbol,
            action=action,
            exchange=exchange,
            pricetype=price_type,
            product=product,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            disclosed_quantity=disclosed_quantity,
        )

    def cancelorder(self, order_id: str, strategy: str) -> Dict[str, Any]:
        """Cancel a specific order."""
        return self._post("cancelorder", order_id=order_id, strategy=strategy)

    def cancelallorder(self, strategy: str) -> Dict[str, Any]:
        """Cancel all open orders."""
        return self._post("cancelallorder", strategy=strategy)

    # ------------------------------------------------------------------ #
    # Position Management
    # ------------------------------------------------------------------ #

    def closeposition(self, strategy: str) -> Dict[str, Any]:
        """Close all open positions."""
        return self._post("closeposition", strategy=strategy)

    def openposition(
        self,
        strategy: str,
        symbol: str,
        exchange: str,
        product: str,
    ) -> Dict[str, Any]:
        """Get open position for a specific instrument."""
        return self._post(
            "openposition",
            strategy=strategy,
            symbol=symbol,
            exchange=exchange,
            product=product,
        )

    # ------------------------------------------------------------------ #
    # Order Status & Tracking
    # ------------------------------------------------------------------ #

    def orderstatus(self, order_id: str, strategy: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        return self._post("orderstatus", order_id=order_id, strategy=strategy)

    def orderbook(self) -> Dict[str, Any]:
        """Get all orders from the order book."""
        return self._post("orderbook")

    def tradebook(self) -> Dict[str, Any]:
        """Get all executed trades."""
        return self._post("tradebook")

    def positionbook(self) -> Dict[str, Any]:
        """Get all current positions."""
        return self._post("positionbook")

    def holdings(self) -> Dict[str, Any]:
        """Get all holdings."""
        return self._post("holdings")

    def funds(self) -> Dict[str, Any]:
        """Get account funds and margin information."""
        return self._post("funds")

    def margin(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate margin requirements for positions."""
        return self._post("margin", positions=positions)

    # ------------------------------------------------------------------ #
    # Market Data
    # ------------------------------------------------------------------ #

    def quotes(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get current quote for a symbol."""
        return self._post("quotes", symbol=symbol, exchange=exchange)

    def multiquotes(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get quotes for multiple symbols."""
        return self._post("multiquotes", symbols=symbols)

    def depth(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get market depth for a symbol."""
        return self._post("depth", symbol=symbol, exchange=exchange)

    def history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str,
        source: str = "api",
    ) -> Union[Dict[str, Any], pd.DataFrame]:
        """
        Get historical OHLCV data.

        Returns a DataFrame when source='db', dict otherwise.
        """
        result = self._post(
            "history",
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            source=source,
        )
        # If the response has data, convert to DataFrame for backward compat
        if isinstance(result, dict) and "data" in result:
            try:
                df = pd.DataFrame(result["data"])
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df.set_index("timestamp", inplace=True)
                df.index.name = "date"
                return df
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------ #
    # Instruments & Search
    # ------------------------------------------------------------------ #

    def search(self, query: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """Search for instruments."""
        if exchange:
            return self._post("search", query=query, exchange=exchange)
        return self._post("search", query=query)

    def symbol(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get symbol information."""
        return self._post("symbol", symbol=symbol, exchange=exchange)

    def instruments(self, exchange: Optional[str] = None) -> Union[Dict[str, Any], pd.DataFrame]:
        """Get instrument master."""
        if exchange:
            result = self._post("instruments", exchange=exchange)
        else:
            result = self._post("instruments")
        # Convert to DataFrame for backward compat
        if isinstance(result, dict) and "data" in result:
            try:
                return pd.DataFrame(result["data"])
            except Exception:
                pass
        return result

    def expiry(
        self,
        symbol: str,
        exchange: str,
        instrumenttype: str = "options",
    ) -> Dict[str, Any]:
        """Get expiry dates."""
        return self._post(
            "expiry",
            symbol=symbol,
            exchange=exchange,
            instrumenttype=instrumenttype,
        )

    def intervals(self) -> Dict[str, Any]:
        """Get available intervals."""
        return self._post("intervals")

    def optionsymbol(
        self,
        underlying: str,
        exchange: str,
        offset: str,
        option_type: str,
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get option symbol."""
        return self._post(
            "optionsymbol",
            underlying=underlying,
            exchange=exchange,
            offset=offset,
            option_type=option_type,
            expiry_date=expiry_date,
        )

    def optionchain(
        self,
        underlying: str,
        exchange: str,
        expiry_date: Optional[str] = None,
        strike_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get option chain data."""
        return self._post(
            "optionchain",
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
            strike_count=strike_count,
        )

    def syntheticfuture(
        self,
        underlying: str,
        exchange: str,
        expiry_date: str,
    ) -> Dict[str, Any]:
        """Calculate synthetic future price."""
        return self._post(
            "syntheticfuture",
            underlying=underlying,
            exchange=exchange,
            expiry_date=expiry_date,
        )

    def optiongreeks(
        self,
        symbol: str,
        exchange: str,
        interest_rate: Optional[float] = None,
        forward_price: Optional[float] = None,
        underlying_symbol: Optional[str] = None,
        underlying_exchange: Optional[str] = None,
        expiry_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate option Greeks."""
        return self._post(
            "optiongreeks",
            symbol=symbol,
            exchange=exchange,
            interest_rate=interest_rate,
            forward_price=forward_price,
            underlying_symbol=underlying_symbol,
            underlying_exchange=underlying_exchange,
            expiry_time=expiry_time,
        )

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def telegram(
        self,
        username: str,
        message: str,
        priority: int = 5,
    ) -> Dict[str, Any]:
        """Send a Telegram alert."""
        return self._post(
            "telegram",
            username=username,
            message=message,
            priority=priority,
        )

    def holidays(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Get trading holidays."""
        if year:
            return self._post("holidays", year=year)
        return self._post("holidays")

    def timings(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange timings."""
        if date:
            return self._post("timings", date=date)
        return self._post("timings")

    def analyzerstatus(self) -> Dict[str, Any]:
        """Get analyzer status."""
        return self._post("analyzerstatus")

    def analyzertoggle(self, mode: bool) -> Dict[str, Any]:
        """Toggle analyzer mode."""
        return self._post("analyzertoggle", mode=mode)
