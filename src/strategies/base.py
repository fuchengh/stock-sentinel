from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Input: DataFrame with OHLCV data
        Output: Dictionary containing:
            - signal: "BUY", "SELL", "HOLD", "PROFIT"
            - reason: string explanation
            - severity: "info", "success", "warning", "danger"
            - price: current price
            - ... other indicators
        """
        pass