"""
Custom Exception Hierarchy for the Trading Bot.

Provides granular, semantically meaningful exceptions for validation errors,
API communication failures, and unexpected runtime issues. Each exception
carries a human-readable message suitable for CLI output.
"""


class TradingBotError(Exception):
    """
    Base exception for all trading bot errors.

    All custom exceptions in this project inherit from this class,
    allowing callers to catch any bot-related error with a single
    except clause when needed.
    """

    def __init__(self, message: str = "An unexpected trading bot error occurred.") -> None:
        self.message = message
        super().__init__(self.message)


class ValidationError(TradingBotError):
    """
    Raised when user-supplied input fails validation.

    Examples:
        - Missing required fields (symbol, quantity).
        - Invalid order type or side.
        - Non-numeric or non-positive quantity/price.
        - Missing price for LIMIT orders.
    """

    def __init__(self, message: str = "Input validation failed.") -> None:
        super().__init__(message)


class BinanceConnectionError(TradingBotError):
    """
    Raised when the bot cannot establish or maintain a connection
    to the Binance Futures Testnet API.

    Covers:
        - Network timeouts.
        - DNS resolution failures.
        - Connection refused / reset errors.
    """

    def __init__(self, message: str = "Failed to connect to Binance API.") -> None:
        super().__init__(message)


class BinanceAPIError(TradingBotError):
    """
    Raised when the Binance API returns a business-logic error.

    Covers:
        - Insufficient margin.
        - Invalid symbol.
        - Rejected orders.
        - Rate-limit violations.

    Attributes:
        status_code: HTTP status code returned by the API.
        error_code:  Binance-specific error code (e.g., -1121).
        api_message: Raw error message from the Binance response.
    """

    def __init__(
        self,
        message: str = "Binance API returned an error.",
        status_code: int | None = None,
        error_code: int | None = None,
        api_message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.api_message = api_message
        # Build a descriptive message incorporating API details.
        details = message
        if error_code is not None or api_message:
            details += f" [code={error_code}, msg={api_message}]"
        super().__init__(details)


class OrderExecutionError(TradingBotError):
    """
    Raised when an order is accepted by the API but fails during
    execution (e.g., partially filled then cancelled).
    """

    def __init__(self, message: str = "Order execution failed.") -> None:
        super().__init__(message)
