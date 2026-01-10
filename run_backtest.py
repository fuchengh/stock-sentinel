import sys
import re
import argparse
from datetime import datetime, timedelta
from src.backtester import Backtester
from dotenv import load_dotenv

def parse_duration(duration_str):
    """
    Parses strings like '2y', '1y6m', '100d' into total days.
    Default to days if no suffix.
    """
    duration_str = duration_str.lower()
    total_days = 0
    
    # Check for years
    y_match = re.search(r'(\d+)y', duration_str)
    if y_match:
        total_days += int(y_match.group(1)) * 365
        
    # Check for months (approx 30 days)
    m_match = re.search(r'(\d+)m', duration_str)
    if m_match:
        total_days += int(m_match.group(1)) * 30
        
    # Check for days
    d_match = re.search(r'(\d+)d', duration_str)
    if d_match:
        total_days += int(d_match.group(1))
        
    # If no suffix, treat as days
    if total_days == 0 and duration_str.isdigit():
        total_days = int(duration_str)
        
    return total_days if total_days > 0 else 365

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Stock Sentinel Backtester")
    parser.add_argument("ticker", type=str, help="Stock Ticker (e.g., NVDA)")
    parser.add_argument("duration", type=str, nargs="?", default="1y", help="Duration (e.g., 2y, 1y6m, 100d)")
    parser.add_argument("-b", "--benchmark", type=str, default="QQQ", help="Benchmark Tickers, comma separated (default: QQQ)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()

    ticker = args.ticker.upper()
    # Split benchmarks by comma and clean up
    benchmarks = [b.strip().upper() for b in args.benchmark.split(",")]
    
    days = parse_duration(args.duration)
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    print(f"🛠️  Initializing Backtest for {ticker} over last {args.duration} ({days} days)...")
    print(f"    Start Date: {start_date}")
    print(f"    Benchmarks: {', '.join(benchmarks)}")
    
    # Initialize Backtester
    bt = Backtester(
        ticker=ticker, 
        start_date=start_date, 
        initial_capital=10000,
        use_ai=True,
        benchmark_tickers=benchmarks,
        verbose=args.verbose
    )
    
    try:
        bt.run()
    except KeyboardInterrupt:
        print("\n🛑 Backtest stopped by user.")
    except Exception as e:
        print(f"\n❌ Error during backtest: {e}")

if __name__ == "__main__":
    main()
