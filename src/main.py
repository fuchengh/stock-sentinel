import os
from dotenv import load_dotenv, dotenv_values
from src.data_loader import AlpacaLoader
from src.strategies import EngineerStrategy
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
    # Debug: Check env vars
    print(f"DEBUG: ALPACA_KEY status: {'FOUND' if os.getenv('ALPACA_KEY') else 'MISSING'}")
    
    # 1. Initialize components
    loader = AlpacaLoader()
    strategy = EngineerStrategy()
    notifier = DiscordNotifier()
    chart_gen = ChartGenerator()
    ai_analyst = AIAnalyst()

    # 2. Get watchlist from environment variable
    raw_watchlist = os.getenv('WATCHLIST', 'ALAB')
    watchlist = [x.strip() for x in raw_watchlist.split(',') if x.strip()]

    print(f"🔍 Starting scan for: {watchlist}")
    results = {}

    # 3. Process each ticker
    for ticker in watchlist:
        print(f"Processing {ticker}...")
        
        # Step A: Get Data
        df = loader.get_weekly_bars(ticker)
        if df is None: continue

        # Step B: Analyze
        analysis = strategy.analyze(df)
        
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
        
        # Log to console
        print(f"  -> {analysis['signal']}: {analysis['reason']}")

    # 4. Send Notification
    notifier.send_report(results)
    print("✅ Scan complete.")

if __name__ == "__main__":
    main()