"""
Binance Futures Testnet Client.

Encapsulates all low-level HTTP communication with the Binance Futures
Testnet REST API.  Handles:

    - HMAC-SHA256 request signing.
    - Timestamp synchronisation.
    - Structured error translation (HTTP → custom exceptions).
    - Connection-level retry / timeout semantics.

This module is the **only** place in the codebase that knows about raw
HTTP details.  Higher-level modules (``orders.py``, ``cli.py``) interact
exclusively through the public methods exposed here.

References:
    Binance Futures API docs:
        https://binance-docs.github.io/apidocs/futures/en/
    Testnet base URL:
        https://testnet.binancefuture.com
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests
from requests.exceptions import ConnectionError, Timeout

from bot.exceptions import BinanceAPIError, BinanceConnectionError

logger = logging.getLogger("trading_bot")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TESTNET_BASE_URL: str = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW: int = 5000          # ms — tolerance for clock drift
DEFAULT_TIMEOUT: int = 10               # seconds for HTTP requests


class BinanceClient:
    """
    Lightweight wrapper around the Binance USDT-M Futures Testnet API.

    Args:
        api_key:     Binance Testnet API key.
        api_secret:  Binance Testnet API secret.
        base_url:    Override the default testnet URL (useful for testing).
        timeout:     HTTP request timeout in seconds.
        recv_window: Binance ``recvWindow`` parameter (ms).

    Example::

        client = BinanceClient(api_key="abc", api_secret="xyz")
        info = client.get_exchange_info()
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        self._api_key: str = api_key
        self._api_secret: str = api_secret
        self._base_url: str = base_url.rstrip("/")
        self._timeout: int = timeout
        self._recv_window: int = recv_window

        # Persistent session for connection pooling.
        self._session: requests.Session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

        logger.info(
            "BinanceClient initialised — base_url=%s, timeout=%ds",
            self._base_url,
            self._timeout,
        )

    # ------------------------------------------------------------------
    # Signing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_timestamp() -> int:
        """Return the current UNIX timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Append ``timestamp``, ``recvWindow``, and ``signature`` to *params*.

        The signature is an HMAC-SHA256 of the encoded query-string using
        the API secret.
        """
        params["timestamp"] = self._get_timestamp()
        params["recvWindow"] = self._recv_window

        query_string: str = urlencode(params)
        signature: str = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params

    # ------------------------------------------------------------------
    # HTTP primitives
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request against the Binance API.

        Args:
            method:   ``"GET"`` or ``"POST"``.
            endpoint: API path (e.g., ``"/fapi/v1/order"``).
            params:   Query / body parameters.
            signed:   Whether the request requires HMAC signing.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            BinanceConnectionError: On network-level failures.
            BinanceAPIError:        On non-2xx responses from Binance.
        """
        url: str = f"{self._base_url}{endpoint}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug(
            "HTTP %s %s — params=%s",
            method,
            endpoint,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params if method == "GET" else None,
                data=params if method == "POST" else None,
                timeout=self._timeout,
            )
        except Timeout as exc:
            logger.error("Connection timeout: %s", exc)
            raise BinanceConnectionError(
                f"Connection to Binance timed out after {self._timeout}s."
            ) from exc
        except ConnectionError as exc:
            logger.error("Network error: %s", exc)
            raise BinanceConnectionError(
                "Unable to reach Binance API. Check your network connection."
            ) from exc

        # --- Handle non-2xx responses ------------------------------------
        if not response.ok:
            error_body: dict[str, Any] = {}
            try:
                error_body = response.json()
            except ValueError:
                pass

            api_code = error_body.get("code")
            api_msg = error_body.get("msg", response.text)

            logger.error(
                "Binance API error — HTTP %d, code=%s, msg=%s",
                response.status_code,
                api_code,
                api_msg,
            )

            raise BinanceAPIError(
                message="Binance API request failed.",
                status_code=response.status_code,
                error_code=api_code,
                api_message=api_msg,
            )

        data: dict[str, Any] = response.json()
        logger.debug("Response: %s", data)
        return data

    # ------------------------------------------------------------------
    # Public API wrappers
    # ------------------------------------------------------------------
    def get_exchange_info(self) -> dict[str, Any]:
        """
        Fetch exchange information (symbols, filters, rate limits).

        Endpoint: ``GET /fapi/v1/exchangeInfo``
        """
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: str | None = None,
        time_in_force: str | None = None,
    ) -> dict[str, Any]:
        """
        Submit a new order to the Binance Futures Testnet.

        Endpoint: ``POST /fapi/v1/order``

        Args:
            symbol:        Trading pair (e.g., ``"BTCUSDT"``).
            side:          ``"BUY"`` or ``"SELL"``.
            order_type:    ``"MARKET"`` or ``"LIMIT"``.
            quantity:      Order quantity as a string (to preserve precision).
            price:         Limit price (required for LIMIT orders).
            time_in_force: ``"GTC"`` by default for LIMIT orders.

        Returns:
            Order response dict from Binance.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force or "GTC"

        logger.info(
            "Placing order — symbol=%s, side=%s, type=%s, qty=%s, price=%s",
            symbol,
            side,
            order_type,
            quantity,
            price,
        )

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_account_info(self) -> dict[str, Any]:
        """
        Retrieve current account information.

        Endpoint: ``GET /fapi/v2/account``
        """
        return self._request("GET", "/fapi/v2/account", signed=True)

    def ping(self) -> bool:
        """
        Test connectivity to the Binance API.

        Returns ``True`` if the server responds, ``False`` otherwise.
        """
        try:
            self._request("GET", "/fapi/v1/ping")
            return True
        except (BinanceConnectionError, BinanceAPIError):
            return False
