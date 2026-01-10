import pandas as pd
from datetime import timedelta
import time
from .data_loader import AlpacaLoader
from .ai_analyst import AIAnalyst
from .strategies.engineer import EngineerStrategy

class Backtester:
    def __init__(self, ticker, start_date=None, end_date=None, initial_capital=10000, use_ai=True, benchmark_tickers=['SPY'], verbose=False, slippage_pct=0.001):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.capital = initial_capital
        self.cash = initial_capital
        self.shares = 0
        self.total_cost = 0 # Track total cost for accurate PnL
        self.use_ai = use_ai
        self.benchmark_tickers = benchmark_tickers
        self.verbose = verbose
        self.slippage_pct = slippage_pct
        
        # Dependencies
        self.loader = AlpacaLoader()
        self.ai = AIAnalyst()
        self.strategy = EngineerStrategy()
        
        # Stats
        self.trades = []
        self.equity_curve = []
        
        # Cache for data
        self.full_df = None
        self.benchmark_dfs = {}

    def load_data(self):
        print(f"🔄 [Backtest] Loading historical data for {self.ticker}...")
        self.full_df = self.loader.get_weekly_bars(self.ticker, limit=None)
        
        if self.benchmark_tickers:
            for b_ticker in self.benchmark_tickers:
                print(f"🔄 [Backtest] Loading benchmark data for {b_ticker}...")
                df = self.loader.get_weekly_bars(b_ticker, limit=None)
                if df is not None:
                    self.benchmark_dfs[b_ticker] = df

        if self.full_df is None or self.full_df.empty:
            raise ValueError(f"No data found for {self.ticker}")
            
        # Filter by date if provided
        # We DO NOT filter by start_date here anymore, because we need prior data 
        # to calculate indicators (warm-up period). We will filter in the run loop.
                
        if self.end_date:
            self.full_df = self.full_df[self.full_df.index <= self.end_date]
            for b_ticker in self.benchmark_dfs:
                self.benchmark_dfs[b_ticker] = self.benchmark_dfs[b_ticker][self.benchmark_dfs[b_ticker].index <= self.end_date]
            
        print(f"✅ Data loaded: {len(self.full_df)} weeks of data.")

    def run(self):
        if self.full_df is None:
            self.load_data()
            
        print(f"🚀 [Backtest] Starting simulation for {self.ticker} (${self.capital})...")
        print("-" * 50)
        
        # Minimum window for indicators (e.g. 20 for EMA)
        min_window = 20
        
        for i in range(min_window, len(self.full_df)):
            # 1. Slice data up to current 'simulation time'
            current_slice = self.full_df.iloc[:i+1].copy()
            current_date = current_slice.index[-1]
            current_date_str = current_date.strftime('%Y-%m-%d')
            
            # Skip if before start_date (Warm-up period)
            if self.start_date and current_date_str < self.start_date:
                continue
            
            # 2. Run Technical Strategy
            analysis = self.strategy.analyze(current_slice)
            signal = analysis['signal']
            price = analysis['price']
            
            # Debug: print weekly status
            # Only print every week if verbose, otherwise just important events
            if self.verbose:
                print(f"    📅 {current_date_str}: ${price:.2f} | {signal} | RSI: {analysis['rsi']:.1f}")
            
            # Record equity
            current_equity = self.cash + (self.shares * price)
            self.equity_curve.append({'date': current_date, 'equity': current_equity})
            
            # 3. Decision Logic
            action = "HOLD"
            
            # Case A: Strategy says BUY
            if signal == "BUY":
                if self.cash > price:
                    verdict = "✅ Agree" # Default if no AI
                    
                    if self.use_ai:
                        print(f"🤖 [AI] Analyzing BUY signal for {current_date_str}...")
                        # Fetch historical news for the week leading up to this Friday
                        start_of_week = (current_date - timedelta(days=7)).strftime('%Y-%m-%d')
                        news = self.loader.get_news_for_period(self.ticker, start_of_week, current_date_str)
                        
                        backtest_config = {
                            'date': current_date_str,
                            'news': news
                        }
                        
                        ai_response = self.ai.get_analysis(self.ticker, analysis, backtest_config)
                        
                        # Verbose AI output
                        if self.verbose:
                            print(f"    📄 AI Raw Response:\n{ai_response}\n")

                        # Simple parsing of AI verdict
                        if "✅ Agree" in ai_response:
                            verdict = "✅ Agree"
                        elif "⚠️ Caution" in ai_response:
                            verdict = "⚠️ Caution"
                        else:
                            verdict = "❌ Disagree"
                            
                        print(f"    -> AI Verdict: {verdict}")
                    
                    # Execute Buy if AI agrees or warns
                    if verdict != "❌ Disagree":
                        # Dynamic Position Sizing
                        base_pct = 0.2
                        confidence_mult = 1.0
                        
                        if verdict == "✅ Agree":
                            confidence_mult = 1.5 
                        elif verdict == "⚠️ Caution":
                            confidence_mult = 0.5 
                            
                        target_amount = self.cash * base_pct * confidence_mult
                        
                        if target_amount > self.cash:
                            target_amount = self.cash
                            
                        quantity = int(target_amount // price)
                        
                        if quantity > 0:
                            self.buy(current_date, price, quantity, reason=f"Tech: {analysis['reason']} | AI: {verdict} (Size: {base_pct*confidence_mult:.0%} of cash)")
                        elif self.verbose:
                            print(f"    ⚠️ Skipped BUY: Calculated size too small for 1 share (Cash: ${self.cash:.2f})")
                
                elif self.verbose:
                     print(f"    ⚠️ Skipped BUY: Insufficient Funds (Cash: ${self.cash:.2f})")

            # Case B: Strategy says SELL or PROFIT
            elif signal == "SELL" or signal == "PROFIT":
                if self.shares > 0:
                    verdict = "✅ Agree" # Default to selling
                    
                    if self.use_ai:
                        print(f"🤖 [AI] Analyzing {signal} signal for {current_date_str}...")
                        start_of_week = (current_date - timedelta(days=7)).strftime('%Y-%m-%d')
                        news = self.loader.get_news_for_period(self.ticker, start_of_week, current_date_str)
                        
                        backtest_config = {'date': current_date_str, 'news': news}
                        
                        ai_response = self.ai.get_analysis(self.ticker, analysis, backtest_config)
                        
                        if self.verbose:
                            print(f"    📄 AI Raw Response:\n{ai_response}\n")

                        if "✅ Agree" in ai_response:
                            verdict = "✅ Agree"
                        elif "⚠️ Caution" in ai_response:
                            verdict = "⚠️ Caution" 
                        else:
                            verdict = "❌ Disagree" 

                        print(f"    -> AI Verdict: {verdict}")

                    # Execute Sell UNLESS AI strongly disagrees
                    if verdict == "❌ Disagree":
                         print(f"✋ [AI] Overrode {signal} signal. Holding position.")
                    else:
                        self.sell(current_date, price, reason=f"Tech: {analysis['reason']} | AI: {verdict}")
                
                elif self.verbose:
                    print(f"    ℹ️  Skipped {signal}: No current holdings.")
            
            # Case C: Stop Loss check
            # EngineerStrategy returns 'SELL' if price < stop_loss, so covered above.

        self.finalize_report()

    def buy(self, date, price, quantity, reason):
        # Apply slippage (Buy higher)
        exec_price = price * (1 + self.slippage_pct)
        cost = quantity * exec_price
        
        self.cash -= cost
        self.shares += quantity
        self.total_cost += cost
        
        print(f"🔵 [BUY]  {date.date()} @ ${exec_price:.2f} (incl. slip) x {quantity} | {reason}")
        self.trades.append({
            'type': 'BUY',
            'date': date,
            'price': exec_price,
            'qty': quantity,
            'reason': reason
        })

    def sell(self, date, price, reason):
        if self.shares > 0:
            # Apply slippage (Sell lower)
            exec_price = price * (1 - self.slippage_pct)
            revenue = self.shares * exec_price
            profit = revenue - self.total_cost
            
            self.cash += revenue
            print(f"🟠 [SELL] {date.date()} @ ${exec_price:.2f} (incl. slip) | PnL: ${profit:.2f} | {reason}")
            
            self.trades.append({
                'type': 'SELL',
                'date': date,
                'price': exec_price,
                'qty': 0, # Sold all
                'reason': reason,
                'pnl': profit
            })
            self.shares = 0
            self.total_cost = 0

    def finalize_report(self):
        final_price = self.full_df.iloc[-1]['close']
        total_equity = self.cash + (self.shares * final_price)
        pnl_pct = ((total_equity - self.capital) / self.capital) * 100
        
        print("\n" + "="*50)
        print("🏁 BACKTEST COMPLETE")
        print(f"Ticker: {self.ticker}")
        print(f"Strategy: {self.strategy.__class__.__name__}")
        print("-" * 20)
        print(f"Initial Capital:  ${self.capital:,.2f}")
        print(f"Final Equity:     ${total_equity:,.2f} ({pnl_pct:+.2f}%)")
        print(f"  - Cash:         ${self.cash:,.2f}")
        print(f"  - Shares Held:  {self.shares} (Value: ${self.shares * final_price:,.2f})")
        
        # Benchmark comparison
        if self.benchmark_dfs:
            print("-" * 20)
            for b_ticker, df in self.benchmark_dfs.items():
                if not df.empty:
                    # Filter benchmark data to match simulation period
                    sim_df = df
                    if self.start_date:
                        sim_df = df[df.index >= self.start_date]
                        
                    if not sim_df.empty:
                        start_price = sim_df.iloc[0]['close']
                        end_price = sim_df.iloc[-1]['close']
                        bench_return = ((end_price - start_price) / start_price) * 100
                        alpha = pnl_pct - bench_return
                        print(f"Benchmark ({b_ticker:4}) Return: {bench_return:+.2f}% | Alpha: {alpha:+.2f}%")

        print("-" * 20)
        print(f"Total Trades:     {len(self.trades)}")
        
        # Win rate
        winning_trades = [t for t in self.trades if t['type'] == 'SELL' and t['pnl'] > 0]
        completed_trades = [t for t in self.trades if t['type'] == 'SELL']
        if completed_trades:
            win_rate = (len(winning_trades) / len(completed_trades)) * 100
            print(f"Win Rate:         {win_rate:.1f}%")
        print("="*50)