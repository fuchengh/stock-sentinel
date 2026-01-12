import yfinance as yf
import pandas as pd
from enum import Enum

class MarketRegime(Enum):
    RISK_ON = "RISK_ON"       # Favorable environment (Yields dropping/stable)
    NEUTRAL = "NEUTRAL"       # Mixed signals
    RISK_OFF = "RISK_OFF"     # Hostile environment (Yields spiking, Dollar strong)

class MacroSentinel:
    def __init__(self):
        # ^TNX: CBOE Interest Rate 10 Year T No (Yield)
        # DX-Y.NYB: US Dollar Index
        self.tickers = ['^TNX', 'DX-Y.NYB'] 
        
    def analyze(self):
        """
        Analyzes macro indicators to determine the current market regime.
        Returns a dict with regime and analysis details.
        """
        try:
            # Fetch last 10 days of data to see short-term trend
            data = yf.download(self.tickers, period="10d", progress=False, threads=False)
            
            # yfinance returns a MultiIndex column structure if downloading multiple tickers.
            # Structure: Close -> Ticker
            # We need to handle single ticker vs multi ticker return structure safely, 
            # though usually with >1 ticker it's MultiIndex.
            
            if 'Close' not in data:
                return self._default_error_response("No Close data found")

            closes = data['Close']
            
            # Handle if one of the tickers failed to download
            if '^TNX' not in closes.columns or 'DX-Y.NYB' not in closes.columns:
                # Fallback: try downloading individually if bulk fails or just one exists
                # For simplicity in this v1, we return Neutral if data is missing
                return self._default_error_response("Missing macro data")

            # 1. Analyze 10-Year Yield (^TNX)
            tnx = closes['^TNX'].dropna()
            if len(tnx) < 5: 
                return self._default_error_response("Insufficient TNX data")
            
            tnx_curr = tnx.iloc[-1]
            tnx_prev_5d = tnx.iloc[-5]
            tnx_change_pct = ((tnx_curr - tnx_prev_5d) / tnx_prev_5d) * 100
            
            # 2. Analyze Dollar Index (DXY)
            dxy = closes['DX-Y.NYB'].dropna()
            if len(dxy) < 5:
                return self._default_error_response("Insufficient DXY data")

            dxy_curr = dxy.iloc[-1]
            dxy_prev_5d = dxy.iloc[-5]
            dxy_change_pct = ((dxy_curr - dxy_prev_5d) / dxy_prev_5d) * 100

            # 3. Determine Regime
            # Logic: 
            # - Yield spiking > 3% in 5 days is DANGEROUS for tech.
            # - DXY spiking > 1% in 5 days is Headwind.
            
            regime = MarketRegime.NEUTRAL
            reason = []

            # Check Yields (The "Killer" of Valuation)
            if tnx_change_pct > 3.0:
                regime = MarketRegime.RISK_OFF
                reason.append(f"⚠️ US 10Y Yield Spiking (+{tnx_change_pct:.2f}% in 5d)")
            elif tnx_change_pct < -3.0:
                # Dropping yields usually good for tech, unless it's recession fear. 
                # For now, treat as Risk On / Support.
                if regime != MarketRegime.RISK_OFF:
                    regime = MarketRegime.RISK_ON
                reason.append(f"✅ US 10Y Yield Cooling ({tnx_change_pct:.2f}% in 5d)")
            else:
                reason.append(f"ℹ️ US 10Y Yield Stable ({tnx_change_pct:.2f}%)")

            # Check Dollar (The Liquidity Constrictor)
            if dxy_change_pct > 1.0:
                # If Yields are already bad, this confirms it. 
                # If Yields are OK, this might drag it to Neutral/Risk Off.
                if regime == MarketRegime.RISK_ON:
                    regime = MarketRegime.NEUTRAL
                elif regime == MarketRegime.NEUTRAL:
                    regime = MarketRegime.RISK_OFF
                
                reason.append(f"⚠️ DXY Strengthening (+{dxy_change_pct:.2f}%)")
            
            elif dxy_change_pct < -1.0:
                reason.append(f"✅ DXY Weakening ({dxy_change_pct:.2f}%)")
                if regime == MarketRegime.NEUTRAL:
                    regime = MarketRegime.RISK_ON

            return {
                "regime": regime.value,
                "tnx_current": tnx_curr,
                "dxy_current": dxy_curr,
                "reason": " | ".join(reason),
                "details": reason
            }

        except Exception as e:
            return self._default_error_response(f"Exception: {str(e)}")

    def _default_error_response(self, msg):
        return {
            "regime": "NEUTRAL",
            "tnx_current": 0.0,
            "dxy_current": 0.0,
            "reason": f"Macro Data Error: {msg}",
            "details": []
        }
