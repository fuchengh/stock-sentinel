# import pandas_ta as ta
import pandas as pd
import numpy as np

class WatchdogStrategy:
    def analyze(self, ticker, df):
        """
        Analyze daily data for anomalies.
        Returns None if normal, or a dict with alert details if anomalous.
        """
        if df is None or len(df) < 14:
            return None
            
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. Percent Change (Compared to Yesterday's Close)
        pct_change = (curr['close'] - prev['close']) / prev['close'] * 100
        
        # 2. Relative Volume (RVOL)
        # Avg volume of past 5 days (excluding today)
        avg_vol = df['volume'].iloc[-6:-1].mean()
        vol_ratio = curr['volume'] / avg_vol if avg_vol > 0 else 0
        
        # 3. RSI Calculation (Wilder's Smoothing)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        
        # Use EWM with alpha=1/14 for standard Wilder's RSI
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        daily_rsi = 100 - (100 / (1 + rs.iloc[-1])) if not np.isnan(rs.iloc[-1]) else 50

        signals = []
        
        # Thresholds
        CRASH_THRESHOLD = -6.0
        SPIKE_THRESHOLD = 6.0
        VOLUME_THRESHOLD = 2.5
        RSI_OVERSOLD = 30

        signals = []

        # A. Flash Crash
        if pct_change < CRASH_THRESHOLD:
            signals.append(f"📉 **Flash Crash Alert**: Dropped {pct_change:.2f}%")
            
        # B. Volume Spike
        if vol_ratio > VOLUME_THRESHOLD:
            signals.append(f"📢 **Volume Spike**: {vol_ratio:.1f}x average volume")
            
        # C. Breakout (Optional, but good context)
        if pct_change > SPIKE_THRESHOLD:
            signals.append(f"🚀 **Breakout**: Gained {pct_change:.2f}%")

        # D. Oversold
        if daily_rsi < RSI_OVERSOLD:
            signals.append(f"💎 **Oversold Zone**: RSI is {daily_rsi:.1f}")

        if signals:
            return {
                'ticker': ticker,
                'type': 'ALERT',
                'color': 0xffa500, # Orange
                'msg': "\n".join(signals),
                'price': curr['close'],
                'change': pct_change
            }
            
        return None
