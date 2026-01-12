import math

class PositionSizer:
    def __init__(self, account_size=10000.0, base_risk_pct=0.01):
        """
        account_size: Total portfolio value (cash + equity).
        base_risk_pct: Baseline risk per trade (e.g., 0.01 = 1%).
        """
        self.account_size = account_size
        self.base_risk_pct = base_risk_pct

    def calculate_size(self, price, stop_loss, macro_regime="NEUTRAL"):
        """
        Calculates the recommended position size based on risk and macro environment.
        """
        # 1. Determine Risk Percentage based on Macro Regime
        # "Giant Jack" Philosophy: Bet big when conditions align, shrink when they don't.
        risk_modifier = {
            "RISK_ON": 1.0,   # Full Size (e.g., 1% risk)
            "NEUTRAL": 0.5,   # Half Size (e.g., 0.5% risk) - "Tiny Test"
            "RISK_OFF": 0.25  # Quarter Size or cash (e.g., 0.25% risk)
        }
        
        # Default to conservative if regime unknown
        modifier = risk_modifier.get(macro_regime, 0.5)
        
        effective_risk_pct = self.base_risk_pct * modifier
        risk_amount = self.account_size * effective_risk_pct
        
        # 2. Calculate Risk Per Share
        # If stop_loss >= price (short logic not fully implemented yet), assume standard distance or error
        # Here we assume Long strategies for now.
        risk_per_share = price - stop_loss
        
        if risk_per_share <= 0:
            # Safety fallback: if stop loss is above price (error), use 2x ATR or 5% of price
            risk_per_share = price * 0.05 
        
        # 3. Calculate Shares
        shares = risk_amount / risk_per_share
        
        # 4. Hard Cap Constraints
        # Never put more than X% of account into a single trade (e.g., 20% max allocation)
        # to prevent "Risk per share" being too small leading to massive leverage.
        max_allocation_amt = self.account_size * 0.25 
        max_shares_allocation = max_allocation_amt / price
        
        final_shares = min(shares, max_shares_allocation)
        final_shares = math.floor(final_shares) # Integer shares
        
        # 5. Position Stats
        position_value = final_shares * price
        actual_risk = final_shares * risk_per_share
        
        return {
            "shares": int(final_shares),
            "position_value": position_value,
            "risk_amount": actual_risk,
            "risk_pct_of_account": (actual_risk / self.account_size) * 100,
            "regime_modifier": modifier,
            "message": f"Risking {effective_risk_pct*100:.2f}% of capital ({macro_regime} mode)"
        }
