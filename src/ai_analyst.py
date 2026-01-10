import requests
import os
import json

class AIAnalyst:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        # Default to a cost-effective but smart model, can be overridden in .env
        self.model = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.0-flash-exp:free') 
        self.language = os.getenv('AI_LANGUAGE', 'en').lower() # en or zh_tw
        self.site_url = "https://github.com/yourusername/stock-sentinel"
        self.app_name = "Stock Sentinel"

    def get_analysis(self, ticker, analysis_data, backtest_config=None):
        """
        Sends technical data to LLM for a second opinion.
        
        backtest_config: Optional dict with {'date': 'YYYY-MM-DD', 'news': [list of strings]}
        """
        if not self.api_key:
            return "AI Analysis skipped (No API Key provided)."

        signal = analysis_data['signal']
        price = analysis_data['price']
        
        # Language instruction
        lang_instruction = "Respond in English."
        if self.language in ['zh', 'zh_tw', 'chinese']:
            lang_instruction = "Respond in Traditional Chinese (繁體中文). Keep professional financial terminology in English where appropriate (e.g., EMA, RSI)."

        # Determine context (Live vs Backtest)
        if backtest_config:
            sim_date = backtest_config.get('date')
            hist_news = backtest_config.get('news', [])
            news_section = "\n".join(hist_news) if hist_news else "No specific news found for this period."
            
            context_instruction = f"""
            *** SIMULATION MODE - STRICT KNOWLEDGE CUTOFF ***
            CURRENT DATE: {sim_date}
            
            You are a Wall Street trader working on {sim_date}.
            You MUST act as if you are living in that moment.
            
            RULES:
            1. You have ZERO knowledge of the future. Do not mention anything that happens after {sim_date}.
            2. Analyze the situation based ONLY on the Technical Indicators provided and the HISTORICAL NEWS below.
            3. If the market sentiment is bearish ON THIS DATE, reflect that fear. Do not use your future knowledge of a recovery to be optimistic.
            
            HISTORICAL NEWS (Context available on {sim_date}):
            {news_section}
            """
            web_plugin = [] # No web search in backtest
            sys_role = f"You are a disciplined financial analyst working on {sim_date}. You strictly ignore all future events."
            
        else:
            # Live Mode
            context_instruction = """
            Use your WEB SEARCH capability to check for any recent news, earnings reports, or macro events 
            that might affect this stock specifically.
            """
            web_plugin = [{"id": "web"}]
            sys_role = "You are a concise financial analyst with web search capabilities."

        prompt = f"""
        You are a senior algorithmic trader and technical analyst. 
        Analyze the following trade signal for {ticker} on a Weekly Timeframe.
        
        {context_instruction}

        Target: {ticker}
        Current Price: ${price:.2f}
        Signal: {signal}
        Reason: {analysis_data['reason']}
        
        Technical Indicators:
        - EMA 20: ${analysis_data['ema']:.2f}
        - RSI 14: {analysis_data['rsi']:.1f}
        - ATR Stop Loss: ${analysis_data['stop_loss']:.2f}

        Task:
        1. Evaluate the signal quality based on technicals.
        2. Incorporate the provided NEWS or web search results (if in live mode).
        3. Assess the Risk/Reward purely based on information available ON THAT DATE.
        4. Provide a 'Confidence Score' (Low/Medium/High) and concise advice.
        5. Suggest a Position Sizing approach (Aggressive, Standard, or Conservative).

        Format output as:
        **Verdict:** [✅ Agree / ❌ Disagree / ⚠️ Caution]
        **Sizing:** [Aggressive / Standard / Conservative]
        **Analysis:** [Your concise analysis]
        
        IMPORTANT: {lang_instruction}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_role},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        if web_plugin:
            data["plugins"] = web_plugin

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content.strip()
            else:
                print(f"⚠️ OpenRouter Error {response.status_code}")
                return "AI Analysis failed (API Error)."
                
        except Exception as e:
            print(f"⚠️ AI Analyst Exception: {e}")
            return f"AI Analysis failed: {e}"

    def get_ticker_candidates(self):
        """
        Asks the AI to find potential trending tickers based on news/sentiment.
        Returns: List[str] of tickers.
        """
        if not self.api_key:
            return []

        prompt = f"""
        You are a financial screener.
        
        Task:
        1. Use WEB SEARCH to identify 5-8 US stocks that have strong positive momentum, upcoming catalysts, or favorable sector trends for the next week.
        2. Focus on liquid, mid-to-large cap stocks.
        3. Return ONLY a JSON list of ticker symbols. Do not output any other text.
        
        Example Output:
        ["NVDA", "AMD", "TSM", "PLTR", "MSFT"]
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a JSON-only financial data provider."},
                {"role": "user", "content": prompt}
            ],
            "plugins": [{"id": "web"}],
            "temperature": 0.5,
            "max_tokens": 150
        }

        try:
            print("  -> Asking AI for trending candidates...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                # Clean up content to ensure it's just the list
                start = content.find('[')
                end = content.find(']') + 1
                if start != -1 and end != -1:
                    json_str = content[start:end]
                    return json.loads(json_str)
                return []
            else:
                print(f"⚠️ OpenRouter Error {response.status_code}")
                return []
                
        except Exception as e:
            print(f"⚠️ AI Candidate Search Exception: {e}")
            return []

    def generate_recommendation_report(self, verified_picks):
        """
        verified_picks: List of dicts, each containing 'ticker' and 'analysis' (from strategy).
        """
        if not self.api_key or not verified_picks:
            return None
        
        # Prepare data for AI
        picks_summary = ""
        for item in verified_picks:
            t = item['ticker']
            a = item['analysis']
            # Pass raw technical data to AI to ensure it uses it
            picks_summary += f"""
            - Ticker: {t}
              Price: ${a['price']:.2f}
              Signal: {a['signal']}
              RSI: {a['rsi']:.1f}
              EMA_20: ${a['ema']:.2f}
              Strategy_Reason: {a['reason']}
            """

        lang_instruction = "Respond in English."
        if self.language in ['zh', 'zh_tw', 'chinese']:
            lang_instruction = "Respond in Traditional Chinese (繁體中文). Maintain English for Tickers and Indicators (RSI, EMA)."

        prompt = f"""
        You are a quantitative analyst reporting on validated strategy signals.
        
        We have filtered a list of stocks using our 'Engineer Strategy'. 
        Here are the stocks that PASSED the algorithm:
        {picks_summary}
        
        Task:
        1. Write a brief "Market Opportunity" summary based on current web search context.
        2. Present the "Validated Picks" list. 
        3. **CRITICAL:** For each pick, you MUST display the Technical Data exactly as provided (Signal, RSI, Strategy Reason). Do not hallucinate different numbers.
        4. Add a brief "Analyst Note" for each, combining the technical setup with any relevant news found via web search.

        Format Example (Strictly follow this structure):
        **🚀 Validated Picks:**
        
        1. **[Ticker]** - $[Price]
           - **Strategy:** [Signal] (RSI: [RSI])
           - **Tech Setup:** [Strategy_Reason]
           - **Analyst Note:** [Your insight on why this setup matters now]

        IMPORTANT: {lang_instruction}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a disciplined financial reporter."},
                {"role": "user", "content": prompt}
            ],
            "plugins": [{"id": "web"}],
            "temperature": 0.5, # Lower temperature for precision
            "max_tokens": 600
        }

        try:
            print("  -> Asking AI to summarize verified picks...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content.strip()
            return None
                
        except Exception as e:
            print(f"⚠️ AI Report Gen Exception: {e}")
            return None

    def analyze_alert(self, ticker, alert_data, news_context=None):
        """
        Analyzes a sudden alert (e.g. Flash Crash) with news context.
        """
        if not self.api_key:
            return None

        prompt = f"""
        You are a financial news analyst.
        
        Event: {ticker} has triggered an alert.
        Alert Details:
        {alert_data['msg']}
        Price: ${alert_data.get('price', 0):.2f} (Change: {alert_data.get('change', 0):.2f}%)
        
        Recent News Headlines:
        {news_context if news_context else "No recent news found via API."}
        
        Task:
        1. Read the alert and the news (if any).
        2. If news exists, explain if the news explains the price movement.
        3. If no news, speculate on technical reasons or market sentiment.
        4. Provide a very short (1-2 sentences) "Reasoning" for the user.

        Output Format:
        **AI Insight:** [Your explanation]
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a concise financial news analyst."},
                {"role": "user", "content": prompt}
            ],
            "plugins": [{"id": "web"}], # Keep web access just in case
            "temperature": 0.5,
            "max_tokens": 200
        }

        try:
            print(f"  -> Asking AI to explain alert for {ticker}...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content.strip()
            return None
                
        except Exception as e:
            print(f"⚠️ AI Alert Analysis Exception: {e}")
            return None

