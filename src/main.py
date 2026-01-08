import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv, dotenv_values
from src.data_loader import AlpacaLoader
from src.strategies import EngineerStrategy
from src.strategies.watchdog import WatchdogStrategy
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
    args = parser.parse_args()
    
    mode = args.mode
    print(f"🚀 Starting Sentinel in {mode} mode.")

    # Debug: Check env vars
    print(f"DEBUG: ALPACA_KEY status: {'FOUND' if os.getenv('ALPACA_KEY') else 'MISSING'}")
    
    # 1. Initialize components
    loader = AlpacaLoader()
    notifier = DiscordNotifier()
    ai_analyst = AIAnalyst() # Moved to global scope
    
    # Check Market Schedule
    try:
        clock = loader.get_clock()
        if clock:
            today_str = datetime.now().strftime('%Y-%m-%d')
            # Check calendar to see if today is a trading day
            calendar = loader.get_calendar(start=today_str, end=today_str)
            
            if not calendar:
                print("📅 Today is a market holiday. System sleeping.")
                sys.exit(0)
                
            print(f"✅ Market is open (or valid trading day). Status: {'Open' if clock.is_open else 'Closed (After/Pre-market)'}")
    except Exception as e:
        print(f"⚠️ Market check warning: {e}")
    
    # Components specific to Weekly mode
    engineer_strategy = EngineerStrategy()
    chart_gen = ChartGenerator()
    
    # Component specific to Daily mode
    watchdog = WatchdogStrategy()

    # 2. Get watchlist from environment variable
    raw_watchlist = os.getenv('WATCHLIST', 'ALAB')
    watchlist = [x.strip() for x in raw_watchlist.split(',') if x.strip()]

    print(f"🔍 Scanning list: {watchlist}")
    results = {}

    # 3. Process each ticker
    for ticker in watchlist:
        print(f"Processing {ticker}...")
        
        if mode == 'WEEKLY':
            # Step A: Get Data
            df = loader.get_weekly_bars(ticker)
            if df is None: continue

            # Step B: Analyze
            analysis = engineer_strategy.analyze(df)
            
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

    # 4. Send Notification
    notifier.send_report(results)

    # 5. Weekly AI Recommendations
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
            rec_text = ai_analyst.generate_recommendation_report(verified_picks)
            if rec_text:
                notifier.send_recommendations(rec_text)
        else:
            print("  -> No AI candidates passed the strategy validation.")

    print("✅ Scan complete.")

if __name__ == "__main__":
    main()