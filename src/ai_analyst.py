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

    def get_analysis(self, ticker, analysis_data):
        """
        Sends technical data to LLM for a second opinion.
        """
        if not self.api_key:
            return "AI Analysis skipped (No API Key provided)."

        signal = analysis_data['signal']
        price = analysis_data['price']
        
        # Language instruction
        lang_instruction = "Respond in English."
        if self.language in ['zh', 'zh_tw', 'chinese']:
            lang_instruction = "Respond in Traditional Chinese (繁體中文). Keep professional financial terminology in English where appropriate (e.g., EMA, RSI)."

        prompt = f"""
        You are a senior algorithmic trader and technical analyst. 
        Analyze the following trade signal for {ticker} on a Weekly Timeframe.
        
        Use your WEB SEARCH capability to check for any recent news, earnings reports, or macro events 
        that might affect this stock specifically.

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
        2. Incorporate recent NEWS or FUNDAMENTALS found via web search.
        3. Check for risks (e.g., upcoming earnings, lawsuits, or industry trends).
        4. Provide a 'Confidence Score' (Low/Medium/High) and concise advice.

        Format output as:
        **Verdict:** [✅ Agree / ❌ Disagree / ⚠️ Caution]
        **Analysis:** [Your concise analysis combining technicals + web search results]
        
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
                {"role": "system", "content": "You are a concise financial analyst with web search capabilities."},
                {"role": "user", "content": prompt}
            ],
            "plugins": [{"id": "web"}], # Enable Web Search Plugin
            "temperature": 0.7,
            "max_tokens": 300
        }

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
                print(f"⚠️ OpenRouter Error {response.status_code}: {response.text}")
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
        ["NVDA", "AMD", "TSLA", "PLTR", "MSFT"]
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
                print(f"⚠️ OpenRouter Error {response.status_code}: {response.text}")
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
