import pandas as pd
import numpy as np
from .base import BaseStrategy

class EngineerStrategy(BaseStrategy):
    def __init__(self, ema_len=20, rsi_len=14, atr_len=14, atr_mult=3.0):
        self.ema_len = ema_len
        self.rsi_len = rsi_len
        self.atr_len = atr_len
        self.atr_mult = atr_mult

    def analyze(self, df):
        """
        Analyze the given DataFrame and return trading signals.
        """
        # 1. Calculate Indicators
        # EMA
        df['EMA'] = df['close'].ewm(span=self.ema_len, adjust=False).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        # Wilder's Smoothing for RSI (alpha = 1/n)
        avg_gain = gain.ewm(alpha=1/self.rsi_len, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.rsi_len, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        # Wilder's Smoothing for ATR
        df['ATR'] = tr.ewm(alpha=1/self.atr_len, adjust=False).mean()
        
        # 2. Get current and last week data
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 3. Extract needed values
        price = curr['close']
        ema = curr['EMA']
        rsi = curr['RSI']
        atr = curr['ATR']
        
        # Define stop loss level: Use EMA minus 1*ATR as trend defense line
        # This is more forgiving than just EMA alone to avoid whipsaws
        
        hard_stop = ema - (atr * 1.0) # Buffer of 1x ATR

        # 4. Signal Logic
        signal = "HOLD"
        reason = "Price within normal fluctuation range"
        severity = "info" # info, success (buy), warning (profit), danger (sell)

        # Logic A: Hard Stop / Trend Reversal (Sell Signal)
        # Must break below EMA AND the buffer zone (hard_stop) to trigger SELL
        if price < hard_stop:
            signal = "SELL"
            reason = f"Breached ATR defense line (${hard_stop:.2f}) - Trend Reversal"
            severity = "danger"
        
        # Logic B: Minor breakdown of EMA (Warning)
        elif price < ema:
            signal = "HOLD" # Hold for now!
            reason = "Breached EMA but holding above ATR defense line. Watch until Friday close."
            severity = "warning"
        
        # Logic C: Buy (Uptrend + (RSI pullback OR Fresh Breakout))
        elif (price > ema) and (curr['RSI'] <= 55 or (prev['close'] < prev['EMA'])):
            signal = "BUY"
            reason = "Trend confirmed + (RSI pullback OR Fresh Breakout)"
            severity = "success"
            
        # Logic D: Take Profit (Overbought)
        elif curr['RSI'] > 75:
            signal = "PROFIT"
            reason = "RSI Overbought (>75). Consider taking partial profits."
            severity = "warning"

        return {
            "price": price,
            "ema": ema,
            "rsi": rsi,
            "stop_loss": hard_stop,
            "signal": signal,
            "reason": reason,
            "severity": severity
        }