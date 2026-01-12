import os
import sys
import argparse
import tempfile
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv, dotenv_values
from src.data_loader import AlpacaLoader
from src.strategies import EngineerStrategy
from src.strategies.watchdog import WatchdogStrategy
from src.strategies.macro import MacroSentinel
from src.strategies.event_backtester import EventBacktester
from src.strategies.position_sizer import PositionSizer
from src.notifier import DiscordNotifier
from src.chart_generator import ChartGenerator
from src.ai_analyst import AIAnalyst

# Force load env vars with debug
print(f"DEBUG: CWD = {os.getcwd()}")
env_path = os.path.join(os.getcwd(), ".env")
print(f"DEBUG: Looking for .env at {env_path}, exists: {os.path.exists(env_path)}")

config = dotenv_values(env_path)
print(f"DEBUG: Keys found in .env: {list(config.keys())}")

for k, v in config.items():
    os.environ[k] = v

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, default='WEEKLY', choices=['WEEKLY', 'DAILY'])
    parser.add_argument('--debug', action='store_true', help='Force run ignoring market schedule')
    args = parser.parse_args()
    
    mode = args.mode
    debug = args.debug
    print(f"🚀 Starting Sentinel in {mode} mode.{' (DEBUG MODE ON)' if debug else ''}")

    # Fix for yfinance 'database is locked' in GitHub Actions
    # Set a unique cache directory for this run
    cache_dir = os.path.join(tempfile.gettempdir(), f"yf_cache_{os.getpid()}")
    try:
        yf.set_tz_cache_location(cache_dir)
        print(f"DEBUG: yfinance cache set to {cache_dir}")
    except Exception as e:
        print(f"DEBUG: Could not set yfinance cache: {e}")

    # Debug: Check env vars
    print(f"DEBUG: ALPACA_KEY status: {'FOUND' if os.getenv('ALPACA_KEY') else 'MISSING'}")
    
    # 1. Initialize components
    loader = AlpacaLoader()
    notifier = DiscordNotifier()
    ai_analyst = AIAnalyst() # Moved to global scope
    macro_sentinel = MacroSentinel()
    event_backtester = EventBacktester()
    engineer_strategy = EngineerStrategy()
    
    # Initialize Position Sizer with Account Size
    # Default to 100,000 (Paper Trading Standard) if not set
    acc_size = float(os.getenv('ACCOUNT_SIZE', '100000'))
    sizer = PositionSizer(account_size=acc_size, base_risk_pct=0.01) # 1% Base Risk

    chart_gen = ChartGenerator()
    watchdog = WatchdogStrategy()

    # 2. Macro Analysis (The "Strategic View")
    print("🌍 Analyzing Macro Environment...")
    macro_data = macro_sentinel.analyze()
    print(f"  -> Regime: {macro_data['regime']}")
    print(f"  -> Reason: {macro_data['reason']}")
    
    # Check Market Schedule
    try:
        clock = loader.get_clock()
        if clock:
            today_str = datetime.now().strftime('%Y-%m-%d')
            # Check calendar to see if today is a trading day
            calendar = loader.get_calendar(start=today_str, end=today_str)
            
            if not calendar:
                if debug:
                    print("📅 Today is a market holiday. DEBUG mode enabled: Forcing run.")
                else:
                    print("📅 Today is a market holiday. System sleeping.")
                    # Optional: Send Macro Report even on holidays?
                    # notifier.send_macro_report(macro_data) 
                    sys.exit(0)
                
            print(f"✅ Market is open (or valid trading day). Status: {'Open' if clock.is_open else 'Closed (After/Pre-market)'}")
    except Exception as e:
        print(f"⚠️ Market check warning: {e}")
    

    # 3. Get watchlist from environment variable
    raw_watchlist = os.getenv('WATCHLIST', 'ALAB')
    watchlist = [x.strip() for x in raw_watchlist.split(',') if x.strip()]

    print(f"🔍 Scanning list: {watchlist}")
    results = {}

    # 4. Process each ticker
    for ticker in watchlist:
        print(f"Processing {ticker}...")
        
        if mode == 'WEEKLY':
            # Step A: Get Data
            df = loader.get_weekly_bars(ticker)
            if df is None: continue

            # Step B: Analyze
            analysis = engineer_strategy.analyze(df)
            
            # Step B.2: Event Backtest (Smart Money Context)
            print(f"  -> Running Event Backtest for {ticker}...")
            event_stats = event_backtester.analyze_earnings_behavior(ticker)
            analysis['event_stats'] = event_stats
            print(f"    -> {event_stats['message']}")

            # Step B.3: Position Sizing (Risk Management)
            # Only calculate if we are considering a position (BUY or even watching)
            # We pass the Macro Regime we found earlier.
            if analysis['signal'] == 'BUY':
                sizing = sizer.calculate_size(
                    price=analysis['price'], 
                    stop_loss=analysis['stop_loss'], 
                    macro_regime=macro_data['regime']
                )
                analysis['sizing'] = sizing
                print(f"    -> ⚖️ Sizing: Buy {sizing['shares']} shares ({sizing['message']})")
            else:
                analysis['sizing'] = None

            # Step C: Generate Chart & AI Analysis if Interesting
            if analysis['signal'] != "HOLD":
                print(f"  -> {analysis['signal']} detected! Generating chart & AI analysis...")
                
                # Generate Chart
                chart_buf = chart_gen.generate_chart(ticker, df, analysis)
                analysis['chart'] = chart_buf
                
                # Get AI Opinion
                print(f"  -> Asking AI for opinion on {ticker}...")
                ai_comment = ai_analyst.get_analysis(ticker, analysis)
                analysis['ai_comment'] = ai_comment
                analysis['ai_model'] = ai_analyst.model
            else:
                analysis['chart'] = None
                analysis['ai_comment'] = None
                analysis['ai_model'] = None
                
            results[ticker] = analysis
            print(f"  -> {analysis['signal']}: {analysis['reason']}")
            
        elif mode == 'DAILY':
            # Step A: Get Daily Data (14 days minimum for RSI)
            df = loader.get_daily_bars(ticker, days=30)
            if df is None: continue
            
            # Step B: Analyze with Watchdog
            alert = watchdog.analyze(ticker, df)
            
            if alert:
                print(f"  -> 🚨 ALERT: {alert['msg']}")
                
                # 1. Fetch News
                print(f"    -> Fetching news for {ticker}...")
                news_text = loader.get_latest_news(ticker)
                
                # 2. AI Analysis
                print(f"    -> Analyzing alert with AI...")
                ai_insight = ai_analyst.analyze_alert(ticker, alert, news_text)
                
                # 3. Append to Alert Msg
                if news_text:
                    alert['msg'] += f"\n\n📰 **News Context:**\n{news_text}"
                
                if ai_insight:
                    alert['msg'] += f"\n\n{ai_insight}"
                    alert['ai_model'] = ai_analyst.model
                    
                results[ticker] = alert
            else:
                print(f"  -> Normal.")

    # 5. Send Notification
    # Inject Macro Data into the results so Notifier sends the visual report in both modes.
    results['MACRO'] = macro_data
        
    notifier.send_report(results)

    # 6. Weekly AI Recommendations
    if mode == 'WEEKLY':
        print("🔮 Generating weekly AI market recommendations...")
        candidates = ai_analyst.get_ticker_candidates()
        print(f"  -> AI suggested candidates: {candidates}")
        
        verified_picks = []
        for cand in candidates:
            cand = cand.upper()
            if cand in watchlist:
                continue # Already analyzed
            
            print(f"  -> Validating candidate {cand} with Engineer Strategy...")
            df_cand = loader.get_weekly_bars(cand)
            if df_cand is None:
                print(f"    -> No data found for {cand}. Skipping.")
                continue
                
            analysis_cand = engineer_strategy.analyze(df_cand)
            
            # We filter for positive or interesting setups.
            # Engineer Strategy returns: BUY (success), PROFIT (warning), HOLD (info/warning), SELL (danger)
            # We want to recommend things that are BUY or maybe just not SELL/Danger?
            # Let's be strict: Only BUY or PROFIT (if momentum is strong).
            if analysis_cand['signal'] in ['BUY', 'PROFIT']:
                print(f"    -> ✅ {cand} Passed! Signal: {analysis_cand['signal']}")
                verified_picks.append({
                    'ticker': cand,
                    'analysis': analysis_cand
                })
            else:
                print(f"    -> ❌ {cand} Rejected. Signal: {analysis_cand['signal']} ({analysis_cand['reason']})")
            
            # Limit to top 3 verified picks
            if len(verified_picks) >= 3:
                print("  -> Found 3 verified picks. Stopping search.")
                break
        
        if verified_picks:
            rec_text = ai_analyst.generate_recommendation_report(verified_picks, macro_data)
            if rec_text:
                notifier.send_recommendations(rec_text)
        else:
            print("  -> No AI candidates passed the strategy validation.")

    print("✅ Scan complete.")

if __name__ == "__main__":
    main()