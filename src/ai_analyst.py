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
