"""
SilverTrade AI Data Fetcher
============================
Fetches historical and real-time market data from the SilverTrade AI Platform API.
Replaces the deprecated external PyPI package dependency.
"""

import json
import os
import sys
from typing import Any, Optional

import requests


class DataFetcher:
    """Fetches market data from the SilverTrade AI Platform API.

    Args:
        api_key: SilverTrade AI API key
        host: SilverTrade AI server URL (e.g. http://platform:5000)
    """

    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None):
        self.api_key = str(api_key).strip() if api_key else None
        self.host = (str(host).strip() if host else "http://127.0.0.1:5000").rstrip("/")
        self.base_url = f"{self.host}/api/v1"

    def _post(self, endpoint: str, **kwargs: Any) -> Any:
        """Make a POST request to the Platform API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        payload = {"apikey": self.api_key}
        payload.update({k: v for k, v in kwargs.items() if v is not None})

        try:
            response = requests.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(
                f"Error: Could not connect to SilverTrade AI at {self.host}",
                file=sys.stderr,
                flush=True,
            )
            return None
        except requests.exceptions.Timeout:
            print(
                f"Error: Request to {url} timed out",
                file=sys.stderr,
                flush=True,
            )
            return None
        except requests.exceptions.HTTPError as e:
            print(
                f"Error: HTTP {e.response.status_code} from {url}: {e.response.text}",
                file=sys.stderr,
                flush=True,
            )
            return None
        except Exception as e:
            print(
                f"Error in API request: {str(e)}", file=sys.stderr, flush=True
            )
            return None

    def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str,
        source: str = "api",
    ):
        """Fetch historical OHLCV data from the Platform API.

        Returns a pandas DataFrame on success, or None on failure.
        """
        import pandas as pd

        try:
            result = self._post(
                "history",
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                source=source,
            )

            if result is None:
                return None

            # Handle error responses
            if isinstance(result, dict) and result.get("status") == "error":
                print(
                    f"Error from API: {result.get('message', 'Unknown error')}",
                    file=sys.stderr,
                    flush=True,
                )
                return None

            # Parse data from response
            data = result.get("data") if isinstance(result, dict) else None
            if not data:
                return None

            df = pd.DataFrame(data)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df.set_index("timestamp", inplace=True)
                df.index.name = "date"

            if df.empty:
                return None

            return df

        except Exception as e:
            print(
                f"Error in get_historical_data: {str(e)}",
                file=sys.stderr,
                flush=True,
            )
            return None

    def get_realtime_data(self, symbol: str, exchange: str) -> Optional[dict]:
        """Fetch real-time quote data from the Platform API."""
        try:
            data = self._post("quotes", symbol=symbol, exchange=exchange)
            return data
        except Exception as e:
            print(
                f"Error in get_realtime_data: {str(e)}",
                file=sys.stderr,
                flush=True,
            )
            return None
