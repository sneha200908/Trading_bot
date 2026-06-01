# 🤖 Binance Futures Testnet Trading Bot

> A production-quality CLI trading bot for placing **MARKET** and **LIMIT** orders on the **Binance USDT-M Futures Testnet**.

Built with clean architecture, comprehensive error handling, rotating-file logging, and an interactive CLI experience.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Setup — Binance Futures Testnet](#-setup--binance-futures-testnet)
- [Environment Variables](#-environment-variables)
- [Usage](#-usage)
  - [Argument Mode](#argument-mode)
  - [Interactive Mode](#interactive-mode)
- [Project Structure](#-project-structure)
- [Architecture](#-architecture)
- [Error Handling](#-error-handling)
- [Logging](#-logging)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## 🎯 Project Overview

This project implements a **command-line trading bot** that communicates with the Binance Futures Testnet API to place simulated futures orders. It is designed as a professional-grade application demonstrating:

- **Clean Architecture** — Separation of concerns across dedicated modules.
- **SOLID Principles** — Single-responsibility classes, dependency injection, open/closed design.
- **Defensive Programming** — Input validation, structured exception hierarchy, graceful error recovery.
- **Observability** — Rotating file logs with structured request/response records.

The bot supports both a **flag-based CLI** for scripting and an **interactive guided mode** for manual use.

---

## ✨ Features

| Feature                        | Description                                                         |
| ------------------------------ | ------------------------------------------------------------------- |
| **MARKET Orders**              | Execute immediate buy/sell at current market price                   |
| **LIMIT Orders**               | Place orders at a specified price with GTC time-in-force             |
| **Interactive CLI**            | Guided prompts with numbered menus and inline validation             |
| **Argument CLI**               | Fully scriptable with `--symbol`, `--side`, `--type`, `--quantity`   |
| **Input Validation**           | Symbol format, side, type, numeric quantity/price, LIMIT price check |
| **Custom Exceptions**          | Granular error hierarchy (`ValidationError`, `BinanceAPIError`, …)   |
| **Rotating Logs**              | 5 MB per file, 5 backups, structured format with timestamps          |
| **ANSI-Coloured Output**       | Green/red for buy/sell, cyan headers, yellow prompts                 |
| **Order Summary Display**      | Pre-execution confirmation and post-execution result details         |
| **Environment-Based Secrets**  | API keys loaded via `.env` — never hardcoded                         |
| **HMAC-SHA256 Signing**        | Secure request signing per Binance specification                     |
| **Connection Pooling**         | Persistent HTTP session for efficient API communication              |

---

## 🚀 Installation

### Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)
- A **Binance Futures Testnet** account

### Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd trading_bot

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🔐 Setup — Binance Futures Testnet

### Create API Keys

1. Visit the **Binance Futures Testnet**: [https://testnet.binancefuture.com/](https://testnet.binancefuture.com/)
2. Log in using your **GitHub** account.
3. Navigate to the **API Key** section in the dashboard.
4. Click **Generate HMAC_SHA256 Key**.
5. Copy both the **API Key** and **Secret Key**.

> ⚠️ **Important**: These are *testnet* keys. They have no access to real funds. The testnet provides virtual USDT for paper trading.

---

## 🔑 Environment Variables

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and paste your keys:

   ```env
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_API_SECRET=your_testnet_api_secret_here
   ```

3. **Never** commit `.env` to version control — it is excluded by `.gitignore`.

---

## 📖 Usage

### Argument Mode

Pass all parameters as command-line flags:

```bash
# MARKET BUY order
python -m bot.cli \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001

# LIMIT SELL order
python -m bot.cli \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 95000

# MARKET SELL order for ETH
python -m bot.cli \
  --symbol ETHUSDT \
  --side SELL \
  --type MARKET \
  --quantity 0.05
```

### Interactive Mode

Launch the guided menu-driven interface:

```bash
python -m bot.cli --interactive
```

**Sample session:**

```
╔══════════════════════════════════════════════════╗
║       BINANCE FUTURES TESTNET TRADING BOT        ║
║              USDT-M Perpetual Futures             ║
╚══════════════════════════════════════════════════╝

Select Symbol:
  1. BTCUSDT
  2. ETHUSDT
  3. BNBUSDT
  4. XRPUSDT
  ...

Choose [1-8]: 1

Select Side:
  1. BUY
  2. SELL

Choose [1-2]: 1

Select Order Type:
  1. MARKET
  2. LIMIT

Choose [1-2]: 1

Enter Quantity (e.g., 0.001): 0.001

========================================
           ORDER SUMMARY
========================================
  Symbol:    BTCUSDT
  Side:      BUY
  Type:      MARKET
  Quantity:  0.001
========================================

✓ Order placed successfully

  Order ID:           123456789
  Status:             FILLED
  Executed Quantity:   0.001
  Average Price:      67500.50
```

---

## 📁 Project Structure

```
trading_bot/
│
├── bot/                        # Core application package
│   ├── __init__.py             # Package metadata and version
│   ├── __main__.py             # Module entry point (python -m bot.cli)
│   ├── cli.py                  # CLI parsing, interactive mode, output formatting
│   ├── client.py               # Binance API client (HTTP, signing, error translation)
│   ├── orders.py               # Order service layer (business logic, logging)
│   ├── validators.py           # Input validation with descriptive error messages
│   ├── exceptions.py           # Custom exception hierarchy
│   └── logging_config.py       # Rotating-file logger configuration
│
├── logs/                       # Runtime log directory (auto-created)
│   └── .gitkeep
│
├── .env                        # API credentials (git-ignored)
├── .env.example                # Template for .env
├── .gitignore                  # Git exclusion rules
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

### Module Responsibilities

| Module              | Responsibility                                                                 |
| ------------------- | ------------------------------------------------------------------------------ |
| `cli.py`            | Parse CLI arguments, run interactive prompts, render output — no business logic |
| `client.py`         | HTTP communication, HMAC signing, connection management, error translation      |
| `orders.py`         | Order orchestration, request/response logging, result parsing                   |
| `validators.py`     | All input validation — symbol, side, type, quantity, price                      |
| `exceptions.py`     | Custom exception hierarchy for typed error handling                             |
| `logging_config.py` | Logger setup with rotating file handler and console output                      |

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌───────────────┐      ┌────────────────┐
│   CLI Layer │─────▶│  Validators  │─────▶│ Order Service │─────▶│ Binance Client │
│  (cli.py)   │      │(validators.py)│      │  (orders.py)  │      │  (client.py)   │
└─────────────┘      └──────────────┘      └───────────────┘      └────────────────┘
       │                                           │                        │
       ▼                                           ▼                        ▼
┌─────────────┐                             ┌─────────────┐        ┌──────────────┐
│   Display   │                             │   Logger    │        │  Binance API  │
│  (stdout)   │                             │  (log file) │        │  (testnet)    │
└─────────────┘                             └─────────────┘        └──────────────┘
```

**Data flows left-to-right.** Each layer has a single responsibility and communicates only with its immediate neighbours. Exceptions flow right-to-left through the hierarchy and are caught at the CLI layer for user-friendly display.

---

## ⚠️ Error Handling

The bot uses a **custom exception hierarchy** to classify every possible failure:

| Exception                | Trigger                                          | User Message                        |
| ------------------------ | ------------------------------------------------ | ----------------------------------- |
| `ValidationError`        | Invalid symbol, side, type, quantity, or price    | Clear description of the violation  |
| `BinanceConnectionError` | Network timeout, DNS failure, connection refused  | "Check your network connection"     |
| `BinanceAPIError`        | HTTP 4xx/5xx from Binance (margin, symbol, etc.) | Binance error code + message        |
| `OrderExecutionError`    | Order accepted but failed during execution        | Execution failure details           |
| `TradingBotError`        | Base catch-all for any bot-related error          | Generic bot error                   |

**Key guarantees:**
- ✅ Raw tracebacks **never** reach the user.
- ✅ Every error is logged with full context to `logs/trading_bot.log`.
- ✅ Exit codes are non-zero on failure for script integration.

---

## 📝 Logging

### Configuration

| Setting          | Value                         |
| ---------------- | ----------------------------- |
| Log file         | `logs/trading_bot.log`        |
| Max file size    | 5 MB                          |
| Backup count     | 5 rotated files               |
| File log level   | `DEBUG` (captures everything) |
| Console level    | `WARNING` (minimal noise)     |

### Log Format

```
2025-01-15 10:30:45,123 | INFO     | trading_bot | orders:place_market_order:142 | ORDER REQUEST — symbol=BTCUSDT, side=BUY, type=MARKET, qty=0.001, price=MARKET
```

### What Gets Logged

- **Request Logs**: timestamp, symbol, side, order type, quantity, price
- **Response Logs**: order ID, status, executed quantity, average price, full response body
- **Error Logs**: validation errors, API errors (with HTTP status + Binance error codes), network errors, unexpected exceptions with full stack traces

---

## 🔮 Future Improvements

- [ ] **Stop-Loss and Take-Profit Orders** — Support `STOP_MARKET` and `TAKE_PROFIT_MARKET` types.
- [ ] **Order Cancellation** — Add `--cancel` flag to cancel open orders by ID.
- [ ] **Position Monitoring** — Real-time display of open positions and unrealised PnL.
- [ ] **WebSocket Streams** — Live price feeds and order status updates.
- [ ] **Strategy Engine** — Pluggable trading strategies (SMA crossover, RSI-based).
- [ ] **Unit Tests** — Comprehensive test suite with mocked API responses.
- [ ] **Docker Support** — Containerised deployment with `docker-compose`.
- [ ] **Rate Limiting** — Client-side request throttling to respect API limits.
- [ ] **Multi-Account Support** — Manage multiple API key pairs.
- [ ] **Configuration File** — YAML/TOML config for default symbols, quantities, and strategies.

---

## 📄 License

This project is developed for educational and demonstration purposes. Use it responsibly on the Binance Futures **Testnet** only.

---

<p align="center">
  <em>Built with ❤️ for the Python Developer Internship Assignment</em>
</p>
#   T r a d i n g _ b o t  
 