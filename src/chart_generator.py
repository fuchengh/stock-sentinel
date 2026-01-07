import mplfinance as mpf
import io
import pandas as pd
import numpy as np

class ChartGenerator:
    def generate_chart(self, ticker, df, analysis):
        """
        Generates a high-fidelity TradingView-style chart.
        """
        # 1. Prepare Data (Last 26 weeks)
        plot_df = df.tail(26).copy()
        
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            plot_df.index = pd.to_datetime(plot_df.index)

        # 2. Define Custom TradingView Style
        # Colors based on TradingView Dark Theme
        mc = mpf.make_marketcolors(
            up='#089981',        # TV Green
            down='#F23645',      # TV Red
            edge={'up': '#089981', 'down': '#F23645'},
            wick={'up': '#089981', 'down': '#F23645'},
            volume={'up': '#089981', 'down': '#F23645'},
            ohlc='inherit'
        )

        s = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mc,
            facecolor='#131722',      # TV Dark Background
            edgecolor='#2a2e39',      # Border color
            gridcolor='#2a2e39',      # Grid color
            gridstyle='dotted',
            y_on_right=True,
            rc={'axes.labelsize': 10, 'xtick.labelsize': 9, 'ytick.labelsize': 9}
        )

        # 3. Add Plots (EMA & Signals)
        addplots = []
        
        # EMA Line (Bright Blue)
        if 'EMA' in plot_df.columns:
            addplots.append(mpf.make_addplot(
                plot_df['EMA'], 
                color='#2962FF', 
                width=2,
                alpha=0.8
            ))

        # Signals (Markers)
        # We need arrays of NaNs, filling only the specific points
        buy_signals = [np.nan] * len(plot_df)
        sell_signals = [np.nan] * len(plot_df)
        
        # Logic: We only want to highlight the *current* signal if it exists on the *last* bar.
        # However, to make the chart look "alive" like the screenshot, 
        # we could technically backtest the signals on previous bars, 
        # but for now, let's just mark the current active signal at the end.
        
        last_idx = -1
        last_close = plot_df['close'].iloc[last_idx]
        
        # Signal Offset
        offset = last_close * 0.06 

        if analysis['signal'] == "BUY":
            buy_signals[last_idx] = plot_df['low'].iloc[last_idx] - offset
        elif analysis['signal'] == "SELL":
            sell_signals[last_idx] = plot_df['high'].iloc[last_idx] + offset

        # Add Marker Plots
        if not all(np.isnan(buy_signals)):
            addplots.append(mpf.make_addplot(
                buy_signals, 
                type='scatter', 
                markersize=120, 
                marker='^', 
                color='#089981' # Match Candle Green
            ))
            
        if not all(np.isnan(sell_signals)):
            addplots.append(mpf.make_addplot(
                sell_signals, 
                type='scatter', 
                markersize=120, 
                marker='v', 
                color='#F23645' # Match Candle Red
            ))

        # 4. Generate Plot
        buf = io.BytesIO()
        
        strategy_name = "Engineer Strategy"
        title = f"{ticker} ({strategy_name}) 1W"
        
        mpf.plot(
            plot_df,
            type='candle',
            style=s,
            addplot=addplots,
            title=dict(title=title, color='white', size=12),
            ylabel='', # Hide label to look cleaner
            volume=True,
            savefig=dict(fname=buf, dpi=120, bbox_inches='tight', facecolor='#131722'), # Ensure outer padding matches bg
            figsize=(10, 5),
            datetime_format='%b %d',
            tight_layout=True,
            scale_width_adjustment=dict(volume=0.6, candle=1.0) # Adjust bar widths
        )
        
        buf.seek(0)
        return buf