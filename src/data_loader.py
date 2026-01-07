import alpaca_trade_api as tradeapi
import pandas as pd
import os
import time

class AlpacaLoader:
    def __init__(self):
        key = os.getenv('ALPACA_KEY')
        secret = os.getenv('ALPACA_SECRET')
        base_url = os.getenv('ALPACA_BASE_URL')
        
        # Auto-detect URL if not provided
        if not base_url:
            if key and key.startswith('PK'):
                base_url = 'https://paper-api.alpaca.markets'
            else:
                base_url = 'https://api.alpaca.markets'
                
        print(f"🔌 Connecting to Alpaca ({base_url})...")
        
        self.api = tradeapi.REST(
            key,
            secret,
            base_url=base_url
        )
        
        # Verify connection
        try:
            acct = self.api.get_account()
            print(f"✅ Connected to Alpaca! Account Status: {acct.status}, Buying Power: {acct.buying_power}")
        except Exception as e:
            print(f"❌ Failed to connect to Alpaca Account: {e}")

    def get_weekly_bars(self, ticker, limit=100):
        """Get weekly bars, and convert to DataFrame"""
        try:
            # Add delay to avoid rate limits
            time.sleep(0.3) 
            
            # Explicitly use IEX feed for free paper data
            # Fetch Daily data and resample to Weekly manually
            from datetime import datetime, timedelta
            # Need enough daily data to form ~100 weekly bars
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
            
            daily_bars = self.api.get_bars(
                ticker, 
                tradeapi.TimeFrame.Day, 
                start=start_date,
                feed='iex' 
            ).df
            
            if daily_bars.empty:
                print(f"⚠️ Warning: No data found for {ticker}")
                return None
            
            # Resample to Weekly (Ending on Friday)
            # Ensure index is datetime
            if not isinstance(daily_bars.index, pd.DatetimeIndex):
                daily_bars.index = pd.to_datetime(daily_bars.index)

            weekly_bars = daily_bars.resample('W-FRI').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Drop rows with NaN (in case of empty weeks)
            weekly_bars.dropna(inplace=True)

            return weekly_bars
        except Exception as e:
            print(f"❌ Error fetching {ticker}: {e}")
            return None