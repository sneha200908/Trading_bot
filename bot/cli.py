"""
Command-Line Interface for the Binance Futures Trading Bot.

Provides two modes of operation:

    1. **Argument mode** — pass all parameters via flags::

        python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    2. **Interactive mode** — guided prompts with validation::

        python -m bot.cli --interactive

The CLI is deliberately thin: it parses input, delegates to the validator
and order service, and renders output.  No business logic lives here.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
from decimal import Decimal

from dotenv import load_dotenv

from bot.client import BinanceClient
from bot.exceptions import (
    BinanceAPIError,
    BinanceConnectionError,
    OrderExecutionError,
    TradingBotError,
    ValidationError,
)
from bot.logging_config import setup_logger
from bot.orders import OrderResult, OrderService
from bot.validators import validate_order_params

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_SYMBOLS: list[str] = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
]

SIDES: list[str] = ["BUY", "SELL"]
ORDER_TYPES: list[str] = ["MARKET", "LIMIT"]

# ANSI colour codes for terminal output.
_GREEN = "\033[92m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

# Force UTF-8 output on Windows to avoid cp1252 encoding errors.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def _print_banner() -> None:
    """Print a branded startup banner."""
    banner = f"""
{_CYAN}{_BOLD}╔══════════════════════════════════════════════════╗
║       BINANCE FUTURES TESTNET TRADING BOT        ║
║              USDT-M Perpetual Futures             ║
╚══════════════════════════════════════════════════╝{_RESET}
"""
    print(banner)


def _print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
) -> None:
    """Display a pre-execution order summary."""
    side_colour = _GREEN if side == "BUY" else _RED

    print(f"\n{_BOLD}{'=' * 40}")
    print(f"           ORDER SUMMARY")
    print(f"{'=' * 40}{_RESET}")
    print(f"  Symbol:    {_CYAN}{symbol}{_RESET}")
    print(f"  Side:      {side_colour}{side}{_RESET}")
    print(f"  Type:      {order_type}")
    print(f"  Quantity:  {quantity}")
    if price is not None:
        print(f"  Price:     {price}")
    print(f"{_BOLD}{'=' * 40}{_RESET}\n")


def _print_success(result: OrderResult) -> None:
    """Display a success message with order execution details."""
    print(f"{_GREEN}{_BOLD}✓ Order placed successfully{_RESET}\n")
    print(f"  Order ID:           {result.order_id}")
    print(f"  Status:             {result.status}")
    print(f"  Executed Quantity:   {result.executed_quantity}")
    print(f"  Average Price:      {result.average_price}")
    print()


def _print_failure(reason: str) -> None:
    """Display a failure message with the error reason."""
    print(f"\n{_RED}{_BOLD}✗ Order placement failed{_RESET}")
    print(f"  Reason: {reason}\n")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------
def _select_from_list(prompt: str, options: list[str]) -> str:
    """
    Present a numbered menu and return the user's selection.

    Re-prompts on invalid input until a valid choice is made.
    """
    print(f"\n{_YELLOW}{_BOLD}{prompt}{_RESET}")
    for idx, option in enumerate(options, 1):
        print(f"  {_DIM}{idx}.{_RESET} {option}")

    while True:
        try:
            raw = input(f"\n{_CYAN}Choose [1-{len(options)}]: {_RESET}").strip()
            choice = int(raw)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print(f"{_RED}  Please enter a number between 1 and {len(options)}.{_RESET}")
        except ValueError:
            print(f"{_RED}  Invalid input. Enter a number.{_RESET}")


def _prompt_value(prompt: str, required: bool = True) -> str | None:
    """Prompt the user for a single value with optional enforcement."""
    while True:
        value = input(f"{_CYAN}{prompt}: {_RESET}").strip()
        if value:
            return value
        if not required:
            return None
        print(f"{_RED}  This field is required.{_RESET}")


def _run_interactive() -> dict[str, str | None]:
    """
    Walk the user through an interactive order builder.

    Returns:
        A dictionary of raw (unvalidated) order parameters.
    """
    _print_banner()
    print(f"{_DIM}  Enter order details using the guided prompts below.{_RESET}")

    symbol = _select_from_list("Select Symbol:", SUPPORTED_SYMBOLS)
    side = _select_from_list("Select Side:", SIDES)
    order_type = _select_from_list("Select Order Type:", ORDER_TYPES)

    quantity = _prompt_value("Enter Quantity (e.g., 0.001)")

    price: str | None = None
    if order_type == "LIMIT":
        price = _prompt_value("Enter Limit Price (e.g., 95000)")

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    """
    Construct the CLI argument parser.

    Returns:
        Configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot — "
            "place MARKET and LIMIT orders from the command line."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001\n"
            "  python -m bot.cli --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3500\n"
            "  python -m bot.cli --interactive\n"
        ),
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive mode with guided prompts.",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Trading pair symbol (e.g., BTCUSDT).",
    )
    parser.add_argument(
        "--side",
        type=str,
        choices=["BUY", "SELL"],
        help="Order side: BUY or SELL.",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        type=str,
        choices=["MARKET", "LIMIT"],
        help="Order type: MARKET or LIMIT.",
    )
    parser.add_argument(
        "--quantity",
        type=str,
        help="Order quantity (e.g., 0.001).",
    )
    parser.add_argument(
        "--price",
        type=str,
        default=None,
        help="Limit price (required for LIMIT orders).",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Primary CLI entry point.

    Orchestrates:
        1. Environment / logger setup.
        2. Input collection (argument or interactive mode).
        3. Validation.
        4. Order execution.
        5. Result presentation.
    """
    # --- Initialise infrastructure ----------------------------------------
    logger = setup_logger()
    load_dotenv()

    api_key: str | None = os.getenv("BINANCE_API_KEY")
    api_secret: str | None = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        _print_failure(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set in the .env file."
        )
        logger.error("Missing API credentials in environment.")
        sys.exit(1)

    # --- Collect inputs ---------------------------------------------------
    parser = _build_parser()
    args = parser.parse_args()

    if args.interactive:
        raw_params = _run_interactive()
    else:
        # Ensure at least the minimum flags were provided.
        if not all([args.symbol, args.side, args.order_type, args.quantity]):
            parser.print_help()
            print(
                f"\n{_RED}Error: --symbol, --side, --type, and --quantity "
                f"are required in non-interactive mode.{_RESET}"
            )
            sys.exit(1)

        raw_params = {
            "symbol": args.symbol,
            "side": args.side,
            "order_type": args.order_type,
            "quantity": args.quantity,
            "price": args.price,
        }

    # --- Validate ---------------------------------------------------------
    try:
        validated = validate_order_params(
            symbol=raw_params["symbol"],
            side=raw_params["side"],
            order_type=raw_params["order_type"],
            quantity=raw_params["quantity"],
            price=raw_params.get("price"),
        )
    except ValidationError as exc:
        _print_failure(str(exc))
        logger.warning("Validation failed: %s", exc)
        sys.exit(1)

    # --- Show summary -----------------------------------------------------
    _print_order_summary(
        symbol=validated["symbol"],         # type: ignore[arg-type]
        side=validated["side"],             # type: ignore[arg-type]
        order_type=validated["order_type"], # type: ignore[arg-type]
        quantity=validated["quantity"],      # type: ignore[arg-type]
        price=validated["price"],           # type: ignore[arg-type]
    )

    # --- Execute order ----------------------------------------------------
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        service = OrderService(client)

        result: OrderResult = service.place_order(
            symbol=validated["symbol"],         # type: ignore[arg-type]
            side=validated["side"],             # type: ignore[arg-type]
            order_type=validated["order_type"], # type: ignore[arg-type]
            quantity=validated["quantity"],      # type: ignore[arg-type]
            price=validated["price"],           # type: ignore[arg-type]
        )

        _print_success(result)

    except ValidationError as exc:
        _print_failure(str(exc))
        logger.warning("Validation error during execution: %s", exc)
        sys.exit(1)

    except BinanceConnectionError as exc:
        _print_failure(str(exc))
        logger.error("Connection error: %s", exc)
        sys.exit(1)

    except BinanceAPIError as exc:
        _print_failure(str(exc))
        logger.error(
            "Binance API error — HTTP %s, code=%s, msg=%s",
            exc.status_code,
            exc.error_code,
            exc.api_message,
        )
        sys.exit(1)

    except OrderExecutionError as exc:
        _print_failure(str(exc))
        logger.error("Order execution error: %s", exc)
        sys.exit(1)

    except TradingBotError as exc:
        _print_failure(str(exc))
        logger.error("Trading bot error: %s", exc)
        sys.exit(1)

    except Exception as exc:
        # Catch-all: never let raw tracebacks reach the user.
        _print_failure("An unexpected error occurred. Check logs for details.")
        logger.critical("Unhandled exception: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
