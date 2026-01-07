# Stock Sentinel 🚀

An automated stock analysis tool that scans your watchlist using the **Engineer Strategy**, generates professional TradingView-style weekly charts, and sends alerts directly to your Discord server.

## ✨ Features

- **Automated Scanning**: Fetches weekly price data for your watchlist using the Alpaca API.
- **Engineer Strategy**: Implements a robust trend-following strategy:
  - **Trend Filter**: 20-Week EMA.
  - **Momentum**: RSI (14) for entry timing and overbought detection.
  - **Dynamic Stop Loss**: Uses ATR (Average True Range) to filter out noise and prevent premature shakeouts.
- **Visual Alerts**: Generates **TradingView-style Candlestick Charts** for actionable signals (BUY/SELL), marked with indicators and signal arrows.
- **Discord Integration**: Sends beautiful embeds with charts, price levels, and reasoning directly to your channel.
- **Free Data Support**: Automatically handles data resampling (Daily -> Weekly) to support free Alpaca/IEX data feeds.

## 🛠️ Strategy Logic

The **Engineer Strategy** is designed to capture medium-to-long-term trends while avoiding whipsaws.

1.  **BUY Signal**:
    - Price is **above** the 20-week EMA (Uptrend).
    - **AND** (RSI $\le$ 55 **OR** Price just broke out above EMA).
2.  **SELL Signal**:
    - Price drops **below** the Hard Stop level.
    - **Hard Stop** = EMA 20 - (1.0 * ATR).
    - *Note: A minor drop below EMA but above the Hard Stop triggers a WARNING (HOLD) instead of a panic sell.*
3.  **PROFIT Signal**:
    - RSI > 75 (Overbought condition).

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ (Compatible with Python 3.14)
- An [Alpaca Markets](https://alpaca.markets/) account (Free "Paper Trading" account is sufficient).
- A Discord Webhook URL.

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/stock-sentinel.git
    cd stock-sentinel
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Mac/Linux:
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

Create a `.env` file in the root directory with the following variables:

```ini
# Alpaca API Credentials
ALPACA_KEY=PKxxxxxxxxxxxxxxxxxx
ALPACA_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Optional: Set base URL manually (default is auto-detected based on Key prefix)
# ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Discord Webhook for notifications
DISCORD_WEBHOOK=https://discord.com/api/webhooks/......
# Your Discord User ID (Optional, for @mentions)
# Enable Developer Mode in Discord -> Right click your profile -> Copy User ID
DISCORD_USER_ID=123456789012345678

# OpenRouter API (Optional, for AI Analysis)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
# Optional: Select Model (default: google/gemini-2.0-flash-exp:free)
# OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
# Optional: AI Output Language (en, zh_tw)
AI_LANGUAGE=zh_tw
```

### Usage

Run the scanner manually:

```bash
python -m src.main
```

**Tip**: You can set this up as a weekly Cron job (e.g., every Friday after market close or Tuesday morning) to automate your investment routine.

## 📂 Project Structure

- `src/main.py`: Entry point. Initializes loaders, strategy, and notifier.
- `src/data_loader.py`: Handles Alpaca API connection and data resampling.
- `src/strategy.py`: Implements the Engineer Strategy logic (EMA, RSI, ATR).
- `src/chart_generator.py`: Uses `mplfinance` to draw charts.
- `src/notifier.py`: Formats and sends Discord Webhook messages.
