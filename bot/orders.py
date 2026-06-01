"""
Order Service Layer.

Sits between the CLI and the raw :class:`~bot.client.BinanceClient`.
Responsibilities:

    1. Accept validated parameters.
    2. Delegate to the Binance client.
    3. Log the full request/response cycle.
    4. Format and return a structured order result.

By isolating order logic here, the CLI stays thin and the client stays
transport-only — each layer has a single reason to change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from bot.client import BinanceClient
from bot.exceptions import OrderExecutionError

logger = logging.getLogger("trading_bot")


# ---------------------------------------------------------------------------
# Data Transfer Object for order results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OrderResult:
    """
    Immutable container for the essential fields of an executed order.

    Attributes:
        order_id:          Binance-assigned order identifier.
        status:            Order status (e.g., ``FILLED``, ``NEW``).
        symbol:            Trading pair.
        side:              ``BUY`` or ``SELL``.
        order_type:        ``MARKET`` or ``LIMIT``.
        executed_quantity:  Quantity that was actually filled.
        average_price:     Volume-weighted average fill price.
        raw_response:      The complete API response (for logging / debugging).
    """

    order_id: int
    status: str
    symbol: str
    side: str
    order_type: str
    executed_quantity: str
    average_price: str
    raw_response: dict[str, Any]


# ---------------------------------------------------------------------------
# Order Service
# ---------------------------------------------------------------------------
class OrderService:
    """
    High-level facade for placing futures orders.

    Args:
        client: An initialised :class:`~bot.client.BinanceClient`.

    Example::

        service = OrderService(client)
        result  = service.place_market_order("BTCUSDT", "BUY", Decimal("0.001"))
        print(result.order_id, result.status)
    """

    def __init__(self, client: BinanceClient) -> None:
        self._client: BinanceClient = client

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_response(response: dict[str, Any]) -> OrderResult:
        """
        Translate a raw Binance order response into an ``OrderResult``.

        Computes the volume-weighted average price from the list of fills
        when available; falls back to ``avgPrice`` or ``"N/A"``.
        """
        fills: list[dict[str, str]] = response.get("fills", [])

        if fills:
            total_qty = sum(Decimal(f["qty"]) for f in fills)
            total_cost = sum(Decimal(f["qty"]) * Decimal(f["price"]) for f in fills)
            avg_price = str(total_cost / total_qty) if total_qty else "N/A"
        else:
            avg_price = response.get("avgPrice", "N/A")

        return OrderResult(
            order_id=response.get("orderId", 0),
            status=response.get("status", "UNKNOWN"),
            symbol=response.get("symbol", ""),
            side=response.get("side", ""),
            order_type=response.get("type", ""),
            executed_quantity=response.get("executedQty", "0"),
            average_price=avg_price,
            raw_response=response,
        )

    def _log_request(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None,
    ) -> None:
        """Log the outgoing order request."""
        logger.info(
            "ORDER REQUEST — symbol=%s, side=%s, type=%s, qty=%s, price=%s",
            symbol,
            side,
            order_type,
            quantity,
            price if price else "MARKET",
        )

    @staticmethod
    def _log_response(result: OrderResult) -> None:
        """Log the order execution result."""
        logger.info(
            "ORDER RESPONSE — order_id=%s, status=%s, executed_qty=%s, avg_price=%s",
            result.order_id,
            result.status,
            result.executed_quantity,
            result.average_price,
        )
        logger.debug("Full response body: %s", result.raw_response)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
    ) -> OrderResult:
        """
        Place a MARKET order on Binance Futures Testnet.

        Args:
            symbol:   Trading pair (e.g., ``"BTCUSDT"``).
            side:     ``"BUY"`` or ``"SELL"``.
            quantity: Amount to trade.

        Returns:
            An ``OrderResult`` with execution details.

        Raises:
            OrderExecutionError: If the API returns an unexpected status.
            BinanceAPIError:     Propagated from the client on API errors.
            BinanceConnectionError: On network-level failures.
        """
        self._log_request(symbol, side, "MARKET", quantity, None)

        response: dict[str, Any] = self._client.place_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=str(quantity),
        )

        result = self._parse_response(response)
        self._log_response(result)
        return result

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """
        Place a LIMIT order on Binance Futures Testnet.

        Args:
            symbol:        Trading pair (e.g., ``"BTCUSDT"``).
            side:          ``"BUY"`` or ``"SELL"``.
            quantity:      Amount to trade.
            price:         Desired limit price.
            time_in_force: Time-in-force policy (default ``"GTC"``).

        Returns:
            An ``OrderResult`` with execution details.

        Raises:
            OrderExecutionError: If the API returns an unexpected status.
            BinanceAPIError:     Propagated from the client on API errors.
            BinanceConnectionError: On network-level failures.
        """
        self._log_request(symbol, side, "LIMIT", quantity, price)

        response: dict[str, Any] = self._client.place_order(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=str(quantity),
            price=str(price),
            time_in_force=time_in_force,
        )

        result = self._parse_response(response)
        self._log_response(result)
        return result

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
    ) -> OrderResult:
        """
        Unified entry point — dispatches to the correct order method
        based on ``order_type``.

        Args:
            symbol:     Trading pair.
            side:       ``"BUY"`` or ``"SELL"``.
            order_type: ``"MARKET"`` or ``"LIMIT"``.
            quantity:   Amount to trade.
            price:      Required for LIMIT orders.

        Returns:
            An ``OrderResult`` dataclass.
        """
        if order_type == "MARKET":
            return self.place_market_order(symbol, side, quantity)

        if order_type == "LIMIT":
            if price is None:
                raise OrderExecutionError("Price is required for LIMIT orders.")
            return self.place_limit_order(symbol, side, quantity, price)

        raise OrderExecutionError(f"Unsupported order type: {order_type}")
