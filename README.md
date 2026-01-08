# Stock Sentinel 🚀

An automated stock analysis tool that scans your watchlist using the **Engineer Strategy**, generates professional TradingView-style weekly charts, and sends alerts directly to your Discord server.

## ✨ Features

- **Automated Scanning**: Fetches weekly price data for your watchlist using the Alpaca API.
- **Engineer Strategy (Weekly)**: Implements a robust trend-following strategy:
  - **Trend Filter**: 20-Week EMA.
  - **Momentum**: RSI (14) for entry timing and overbought detection.
  - **Dynamic Stop Loss**: Uses ATR (Average True Range) to filter out noise and prevent premature shakeouts.
- **Watchdog Strategy (Daily)**: Monitors your portfolio for:
  - **Flash Crashes**: Sudden >6% drops.
  - **Volume Spikes**: Unusual trading activity (>2.5x average).
  - **Smart Context**: Fetches relevant **News** and uses **AI** to explain *why* the alert happened.
- **AI Analyst**: 
  - Second opinion on all signals.
  - Generates weekly market recommendations.
  - Explains daily alerts with news context.
- **Visual Alerts**: Generates **TradingView-style Candlestick Charts** for actionable signals.
- **Discord Integration**: Sends beautiful embeds with charts, price levels, and reasoning directly to your channel.

## 🛠️ Strategy Logic

### 1. Engineer Strategy (Weekly)
Designed to capture medium-to-long-term trends.
- **BUY**: Price > 20 EMA + (RSI $\le$ 55 or Breakout).
- **SELL**: Price < Hard Stop (EMA - 1ATR).
- **PROFIT**: RSI > 75.

### 2. Watchdog Strategy (Daily)
Designed for risk management.
- Alerts on significant daily anomalies (Crashes, Breakouts, Volume Spikes).
- Automatically fetches news to provide context.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ (Compatible with Python 3.14)
- An [Alpaca Markets](https://alpaca.markets/) account.
- A Discord Webhook URL.
- (Optional) OpenRouter API Key for AI features.

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
# Custom Bot Avatar URL (Optional)
DISCORD_AVATAR_URL=https://i.imgur.com/dJouyw2.jpeg

# OpenRouter API (Optional, for AI Analysis)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
# Optional: Select Model (default: google/gemini-2.0-flash-exp:free)
# OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
# Optional: AI Output Language (en, zh_tw)
AI_LANGUAGE=zh_tw
# Watchlist (Comma separated)
WATCHLIST=ALAB,NVDA,TSLA,MSFT
```

### Usage

**Weekly Scan (Trend Analysis + Portfolio Check):**
Run this on weekends or Friday market close.
```bash
python src/main.py --mode WEEKLY
```

**Daily Watchdog (Anomalies + News):**
Run this daily after market close.
```bash
python src/main.py --mode DAILY
```

**Tip**: You can set this up as a weekly Cron job (e.g., every Friday after market close or Tuesday morning) to automate your investment routine.

## 📂 Project Structure

- `src/main.py`: Entry point. Switches between WEEKLY and DAILY modes.
- `src/data_loader.py`: Handles Alpaca API connection, data resampling, and news fetching.
- `src/strategies/`:
    - `engineer.py`: Weekly trend following logic.
    - `watchdog.py`: Daily anomaly detection logic.
- `src/ai_analyst.py`: Interacts with LLMs for insights and signal validation.
- `src/chart_generator.py`: Uses `mplfinance` to draw charts.
- `src/notifier.py`: Formats and sends Discord Webhook messages.
