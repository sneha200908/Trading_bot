"""
Allow running the bot package as a module.

Usage:
    python -m bot.cli [arguments]

This file simply delegates to the CLI entry point.
"""

from bot.cli import main

if __name__ == "__main__":
    main()
