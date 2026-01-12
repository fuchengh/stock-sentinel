import yfinance as yf
import pandas as pd
import numpy as np
from datetime import timedelta

class EventBacktester:
    def __init__(self):
        pass

    def analyze_earnings_behavior(self, ticker, lookback_quarters=8):
        """
        Analyzes how the stock price reacts to the last N earnings events.
        
        Returns:
            dict: Statistics about post-earnings gaps and drifts.
        """
        try:
            # 1. Fetch Earnings Dates
            t = yf.Ticker(ticker)
            
            # yfinance earnings_dates often returns a dataframe with index as Timestamp
            try:
                earnings = t.earnings_dates
                if earnings is None or earnings.empty:
                    return self._empty_result(f"No earnings dates found for {ticker}")
            except Exception as e:
                # Sometimes yf structure changes or fails
                return self._empty_result(f"Earnings fetch failed: {str(e)}")

            # Filter for past dates only
            now = pd.Timestamp.now().tz_localize(None)
            
            # Clean up index: remove timezone if present for comparison
            if earnings.index.tz is not None:
                earnings.index = earnings.index.tz_localize(None)

            past_earnings = earnings[earnings.index < now].sort_index(ascending=False).head(lookback_quarters)
            
            if past_earnings.empty:
                return self._empty_result("No past earnings found")

            # 2. Fetch Price History covering these events
            # We need enough buffer. 8 quarters ~ 2 years. Let's get 3 years.
            start_date = past_earnings.index.min() - timedelta(days=30)
            hist = t.history(start=start_date)
            
            if hist.empty:
                return self._empty_result("No price history found")

            # Remove timezone from hist index for easier matching
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)

            results = []

            for date in past_earnings.index:
                # Find the closest trading day ON or AFTER the earnings date
                # If earnings are After Market Close (AMC), the reaction is next day.
                # If Before Market Open (BMO), reaction is same day.
                # Since we don't always know AMC/BMO perfectly, we look at the change 
                # from "Day Before" to "Day After".
                
                # Locating the event index in price history
                # We search for the date in the index.
                
                # Simple logic: Reaction Day (T0) is the first trading day >= Earnings Date
                # BUT, if earnings date is a trading day, and it was AMC, the gap is next day.
                # Safe bet: Measure Close(T-1) vs Open(T+1) or Close(T+1).
                
                # Let's find T (Earnings Date)
                idx_loc = hist.index.get_indexer([date], method='nearest')[0]
                if idx_loc == -1: continue
                
                # Ensure we have enough data before and after
                if idx_loc < 1 or idx_loc >= len(hist) - 5:
                    continue
                
                # Define T-1 (Pre-Event) and T+1 (Post-Event Reaction)
                # Note: yfinance earnings dates are often the reported date.
                # We analyze the immediate impact: T-1 Close vs T+1 Close (2 day window captures the event safely)
                # Or T-1 Close vs T0 Close.
                
                # Let's use T-1 Close as baseline.
                t_minus_1 = hist.iloc[idx_loc - 1]
                t_0 = hist.iloc[idx_loc]       # Event Day
                t_plus_1 = hist.iloc[idx_loc + 1] # Next Day
                t_plus_5 = hist.iloc[min(idx_loc + 5, len(hist)-1)] # 1 Week Later

                # Metric 1: Immediate Reaction (Gap + Day Move)
                # (Close of T+1 - Close of T-1) / Close of T-1
                # We use T+1 to be safe about AMC/BMO timing differences.
                pct_move_immediate = (t_plus_1['Close'] - t_minus_1['Close']) / t_minus_1['Close'] * 100
                
                # Metric 2: 1-Week Drift (Trend Continuation)
                # (Close of T+5 - Close of T+1) / Close of T+1
                pct_drift_week = (t_plus_5['Close'] - t_plus_1['Close']) / t_plus_1['Close'] * 100

                results.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'immediate_move': pct_move_immediate,
                    'drift_week': pct_drift_week
                })

            # 3. Compile Statistics
            if not results:
                return self._empty_result("Insufficient data points for statistics")

            moves = [r['immediate_move'] for r in results]
            drifts = [r['drift_week'] for r in results]
            
            avg_move = np.mean(moves)
            win_rate = sum(1 for x in moves if x > 0) / len(moves) * 100 # "Win" = Positive reaction
            
            # Smart Money Logic:
            # If stock usually pops (Move > 0) but then fades (Drift < 0), that's a "Fade the Rip" signal.
            # If stock drops (Move < 0) but recovers (Drift > 0), that's "Buy the Dip".
            
            fade_probability = sum(1 for r in results if r['immediate_move'] > 0 and r['drift_week'] < 0) / len(results) * 100
            
            summary = {
                "events_analyzed": len(results),
                "avg_reaction": avg_move,
                "win_rate": win_rate, # % of times it went UP after earnings
                "fade_rip_prob": fade_probability, # % of times it popped then dropped
                "details": results, # List of dicts
                "message": self._generate_insight(avg_move, win_rate, fade_probability)
            }
            
            return summary

        except Exception as e:
            return self._empty_result(f"Analysis error: {str(e)}")

    def _empty_result(self, msg):
        return {
            "events_analyzed": 0,
            "avg_reaction": 0.0,
            "win_rate": 0.0,
            "fade_rip_prob": 0.0,
            "details": [],
            "message": f"No Data ({msg})"
        }

    def _generate_insight(self, avg_move, win_rate, fade_prob):
        """Generates a human-readable one-liner."""
        trend = "Bullish" if avg_move > 0 else "Bearish"
        
        if win_rate > 75:
            return f"🔥 High Probability Winner ({win_rate:.0f}% Win Rate). Avg Move: {avg_move:.1f}%"
        elif win_rate < 25:
            return f"⚠️ High Probability Loser ({win_rate:.0f}% Win Rate). Avg Move: {avg_move:.1f}%"
        
        if fade_prob > 50:
            return f"📉 'Fade the Rip' Alert! Often pops then drops (Fade Prob: {fade_prob:.0f}%)."
            
        return f"Neutral/Mixed History. Avg Reaction: {avg_move:.1f}%"
