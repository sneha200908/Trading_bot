"""
Centralised Logging Configuration.

Sets up a rotating-file logger that writes structured log records to
``logs/trading_bot.log``.  A secondary stream handler emits condensed
output to ``stderr`` so the CLI stays clean while the log file captures
full diagnostic detail.

Usage:
    from bot.logging_config import setup_logger
    logger = setup_logger()
    logger.info("Bot started")
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE: str = os.path.join(LOG_DIR, "trading_bot.log")
MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB per log file
BACKUP_COUNT: int = 5             # keep 5 rotated backups
LOGGER_NAME: str = "trading_bot"

# Detailed format for the log file.
FILE_FORMAT: str = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
)

# Compact format for console output (only warnings and above).
CONSOLE_FORMAT: str = "%(levelname)s: %(message)s"


def setup_logger(
    level: int = logging.DEBUG,
    console_level: int = logging.CRITICAL,
) -> logging.Logger:
    """
    Create and return the application-wide logger.

    The logger is configured **once**; subsequent calls return the same
    logger instance without adding duplicate handlers.

    Args:
        level:         Minimum severity written to the log *file*.
        console_level: Minimum severity printed to the *console*.

    Returns:
        A configured :class:`logging.Logger` bound to the name
        ``trading_bot``.
    """
    logger = logging.getLogger(LOGGER_NAME)

    # Prevent adding handlers more than once (e.g., when the module is
    # imported from both cli.py and orders.py).
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Ensure the log directory exists.
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    # --- Rotating file handler -------------------------------------------
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    logger.addHandler(file_handler)

    # --- Console handler (stderr) ----------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    logger.addHandler(console_handler)

    logger.debug("Logger initialised — file: %s", LOG_FILE)
    return logger
