"""
Input Validation Module.

Provides a single ``validate_order_params`` entry point that checks every
user-supplied field and raises :class:`~bot.exceptions.ValidationError`
with a descriptive message on the first violation found.

Validation rules are deliberately strict:
    - ``symbol``: required, non-empty, uppercase alphanumeric.
    - ``side``:   must be ``BUY`` or ``SELL``.
    - ``order_type``: must be ``MARKET`` or ``LIMIT``.
    - ``quantity``: required, numeric, > 0.
    - ``price``:  mandatory when ``order_type`` is ``LIMIT``; numeric, > 0.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from bot.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------
VALID_SIDES: frozenset[str] = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES: frozenset[str] = frozenset({"MARKET", "LIMIT"})

# Binance symbols are uppercase letters + digits (e.g., BTCUSDT, 1000PEPEUSDT).
_SYMBOL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z0-9]{2,20}$")


def _validate_symbol(symbol: str | None) -> str:
    """Return the validated symbol or raise ``ValidationError``."""
    if not symbol:
        raise ValidationError("Symbol is required and cannot be empty.")

    symbol = symbol.strip()

    if symbol != symbol.upper():
        raise ValidationError(
            f"Symbol must be uppercase. Received: '{symbol}'. "
            f"Did you mean '{symbol.upper()}'?"
        )

    if not _SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only uppercase letters and digits are allowed (e.g., BTCUSDT)."
        )

    return symbol


def _validate_side(side: str | None) -> str:
    """Return the validated side or raise ``ValidationError``."""
    if not side:
        raise ValidationError("Order side is required (BUY or SELL).")

    side = side.strip().upper()

    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid order side: '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )

    return side


def _validate_order_type(order_type: str | None) -> str:
    """Return the validated order type or raise ``ValidationError``."""
    if not order_type:
        raise ValidationError("Order type is required (MARKET or LIMIT).")

    order_type = order_type.strip().upper()

    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )

    return order_type


def _validate_quantity(quantity: str | float | None) -> Decimal:
    """Return the validated quantity as a ``Decimal`` or raise ``ValidationError``."""
    if quantity is None:
        raise ValidationError("Quantity is required.")

    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        raise ValidationError(
            f"Quantity must be a valid number. Received: '{quantity}'."
        )

    if qty <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero. Received: {qty}."
        )

    return qty


def _validate_price(price: str | float | None, order_type: str) -> Decimal | None:
    """
    Validate the price field.

    For LIMIT orders the price is mandatory and must be numeric > 0.
    For MARKET orders the price is ignored (returns ``None``).
    """
    if order_type == "MARKET":
        # Price is irrelevant for market orders.
        return None

    # --- LIMIT order: price is mandatory ----------------------------------
    if price is None:
        raise ValidationError("Price is required for LIMIT orders.")

    try:
        p = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValidationError(
            f"Price must be a valid number. Received: '{price}'."
        )

    if p <= 0:
        raise ValidationError(
            f"Price must be greater than zero. Received: {p}."
        )

    return p


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_order_params(
    symbol: str | None,
    side: str | None,
    order_type: str | None,
    quantity: str | float | None,
    price: str | float | None = None,
) -> dict[str, str | Decimal | None]:
    """
    Validate all order parameters and return a sanitised parameter dict.

    Args:
        symbol:     Trading pair (e.g., ``"BTCUSDT"``).
        side:       ``"BUY"`` or ``"SELL"``.
        order_type: ``"MARKET"`` or ``"LIMIT"``.
        quantity:   Amount to trade (must be numeric > 0).
        price:      Required only for ``LIMIT`` orders (numeric > 0).

    Returns:
        A dictionary with validated and normalised values::

            {
                "symbol":     "BTCUSDT",
                "side":       "BUY",
                "order_type": "MARKET",
                "quantity":   Decimal("0.001"),
                "price":      None,
            }

    Raises:
        ValidationError: If any field fails validation.
    """
    validated_symbol = _validate_symbol(symbol)
    validated_side = _validate_side(side)
    validated_type = _validate_order_type(order_type)
    validated_qty = _validate_quantity(quantity)
    validated_price = _validate_price(price, validated_type)

    return {
        "symbol": validated_symbol,
        "side": validated_side,
        "order_type": validated_type,
        "quantity": validated_qty,
        "price": validated_price,
    }
