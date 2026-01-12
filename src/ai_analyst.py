import requests
import os
import json
import re
import time

class AIAnalyst:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        # Default to a cost-effective but smart model, can be overridden in .env
        self.model = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.0-flash-exp:free') 
        self.language = os.getenv('AI_LANGUAGE', 'en').lower() # en or zh_tw
        self.site_url = "https://github.com/yourusername/stock-sentinel"
        self.app_name = "Stock Sentinel"

    def _clean_text(self, text):
        """
        Cleans up raw XML tags from Grok/OpenRouter output.
        Converts <grok:render...><argument...>10</argument>...</grok:render> to [10].
        Also attempts to preserve any markdown links if they exist.
        """
        if not text or not isinstance(text, str): return text
        
        # 1. Aggressive XML Cleaner
        # Pattern A: Try to find citation_id
        pattern_id = r'<grok:render[^>]*>.*?<argument name="citation_id">(\\d+)</argument>.*?</grok:render>'
        text = re.sub(pattern_id, r' [\1] ', text, flags=re.DOTALL)
        
        # Pattern B: Cleanup any remaining grok tags that didn't match Pattern A
        pattern_residual = r'<grok:[^>]+>.*?</grok:[^>]+>'
        text = re.sub(pattern_residual, '', text, flags=re.DOTALL)
        
        # Cleanup double spaces created by replacement
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _call_ai(self, messages, schema=None, max_retries=2, plugins=None):
        """
        Unified method to call AI with retry logic and JSON schema support.
        """
        if not self.api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }

        # Prepare response format
        response_format = {"type": "json_object"}
        if schema:
            response_format = {
                "type": "json_schema",
                "json_schema": schema
            }

        data = {
            "model": self.model,
            "messages": messages,
            "response_format": response_format,
            "temperature": 0.5,
            "max_tokens": 1000
        }

        if plugins:
            data["plugins"] = plugins

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(data),
                    timeout=45
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # 1. Parse JSON
                    parsed = json.loads(content)
                    
                    # 2. Clean all string fields in the parsed JSON (to preserve citations and remove XML)
                    def clean_json(obj):
                        if isinstance(obj, dict):
                            return {k: clean_json(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [clean_json(v) for v in obj]
                        elif isinstance(obj, str):
                            return self._clean_text(obj)
                        return obj
                    
                    return clean_json(parsed)
                
                else:
                    print(f"⚠️ AI API Error (Attempt {attempt+1}): {response.status_code} - {response.text}")
            
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ AI Call Exception (Attempt {attempt+1}): {e}")
            
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                data["temperature"] += 0.1 # Increase entropy slightly on retry
        
        return None

    def get_analysis(self, ticker, analysis_data, backtest_config=None):
        """
        Sends technical data to LLM for a second opinion using JSON Schema.
        """
        signal = analysis_data['signal']
        price = analysis_data['price']
        
        # Language instruction
        lang_instruction = "Respond in English."
        if self.language in ['zh', 'zh_tw', 'chinese']:
            lang_instruction = "Respond in Traditional Chinese (繁體中文) for the **analysis** field. **CRITICAL:** Keep financial terms (e.g., EMA, RSI) in English."

        # Define Schema
        schema = {
            "name": "stock_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "verdict": { "type": "string", "description": "Agree, Disagree, or Caution" },
                    "confidence": { "type": "string", "description": "Low, Medium, or High" },
                    "sizing": { "type": "string", "description": "Aggressive, Standard, or Conservative" },
                    "analysis": { "type": "string", "description": "Detailed reasoning with citations" }
                },
                "required": ["verdict", "confidence", "sizing", "analysis"]
            }
        }

        # Context construction
        if backtest_config:
            sim_date = backtest_config.get('date')
            hist_news = backtest_config.get('news', [])
            news_section = "\n".join(hist_news) if hist_news else "No specific news found."
            context = f"STRICT KNOWLEDGE CUTOFF: Act as if today is {sim_date}. Knowledge of the future is FORBIDDEN.\nRecent News: {news_section}"
            plugins = None
        else:
            context = "Use WEB SEARCH to check for any recent news or macro events affecting this stock."
            plugins = [{"id": "web"}]

        messages = [
            {"role": "system", "content": "You are a concise financial analyst outputting structured JSON."},
            {"role": "user", "content": f"""
                Analyze {ticker} at ${price:.2f}. Strategy suggests: {signal} ({analysis_data['reason']}).
                Technical Data: EMA 20: ${analysis_data['ema']:.2f}, RSI 14: {analysis_data['rsi']:.1f}, Stop Loss: ${analysis_data['stop_loss']:.2f}.
                
                {context}
                
                Instructions:
                1. Language: {lang_instruction}
                2. CITATIONS: Use **[Source Name](URL)** format for all references within the 'analysis' field.
                """}
        ]

        result = self._call_ai(messages, schema=schema, plugins=plugins)
        
        if result:
            v = result['verdict']
            if 'Agree' in v: v = "✅ " + v
            elif 'Disagree' in v: v = "❌ " + v
            elif 'Caution' in v: v = "⚠️ " + v
            
            return (
                f"**Verdict:** {v}\n"
                f"**Confidence:** {result['confidence']}\n"
                f"**Sizing:** {result['sizing']}\n"
                f"**Analysis:** {result['analysis']}"
            )
        return "AI Analysis failed to provide structured output."

    def get_ticker_candidates(self):
        """
        Asks the AI to find potential trending tickers.
        """
        schema = {
            "name": "ticker_candidates",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "items": { "type": "string" }
                    }
                },
                "required": ["candidates"]
            }
        }

        messages = [
            {"role": "system", "content": "You are a financial screener."},
            {"role": "user", "content": "Identify 5-8 US stocks with strong momentum or catalysts. Focus on liquid, mid-to-large cap stocks."}
        ]

        print("  -> Asking AI for trending candidates...")
        result = self._call_ai(messages, schema=schema, plugins=[{"id": "web"}])
        return result.get('candidates', []) if result else []

    def generate_recommendation_report(self, verified_picks, macro_data=None):
        """
        verified_picks: List of dicts, each containing 'ticker' and 'analysis'.
        """
        if not verified_picks: return None

        # Prepare Data
        picks_data = [{
            "ticker": p['ticker'],
            "price": f"{p['analysis']['price']:.2f}",
            "signal": p['analysis']['signal'],
            "reason": p['analysis']['reason']
        } for p in verified_picks]

        macro_text = "N/A"
        if macro_data:
            macro_text = f"Regime: {macro_data['regime']}, Reason: {macro_data['reason']}"

        schema = {
            "name": "recommendation_report",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "market_summary": { "type": "string" },
                    "picks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": { "type": "string" },
                                "note": { "type": "string", "description": "Analyst perspective with citations" }
                            },
                            "required": ["ticker", "note"]
                        }
                    }
                },
                "required": ["market_summary", "picks"]
            }
        }

        lang_name = "Traditional Chinese (繁體中文)" if self.language in ['zh', 'zh_tw', 'chinese'] else "English"

        messages = [
            {"role": "system", "content": "You are a quantitative analyst."},
            {"role": "user", "content": f"""
                Macro Context: {macro_text}
                Verified Strategy Picks: {json.dumps(picks_data)}
                
                Task:
                1. Write a 'market_summary' based on the macro regime.
                2. Write a 'note' for each pick combining technicals and web-searched news.
                3. Language: {lang_name}.
                4. CITATIONS: Use **[Source Name](URL)** format for references.
                """}
        ]

        print("  -> Asking AI to summarize verified picks...")
        result = self._call_ai(messages, schema=schema, plugins=[{"id": "web"}], max_retries=2)

        if result:
            summary_title = "市場機會：" if "Chinese" in lang_name else "Market Opportunity:"
            report = f"**{summary_title}**\n{result['market_summary']}\n\n**🚀 Validated Picks:**\n\n"
            
            # Map original data for price/signal
            tech_map = {p['ticker']: p for p in picks_data}
            for p in result['picks']:
                t = p['ticker']
                tech = tech_map.get(t)
                if tech:
                    report += f"1. **[{t}]** - ${tech['price']}\n   - **Strategy:** {tech['signal']}\n   - **Analyst Note:** {p['note']}\n\n"
            return report.strip()
        
        return None

    def analyze_alert(self, ticker, alert_data, news_context=None):
        """
        Analyzes a sudden alert.
        """
        price_str = f"{alert_data.get('price', 0):.2f}"
        change_str = f"{alert_data.get('change', 0):.2f}"
        news_text = news_context if news_context else "No news found via API."

        schema = {
            "name": "alert_analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "insight": { "type": "string", "description": "1-2 sentence explanation of the event" }
                },
                "required": ["insight"]
            }
        }

        messages = [
            {"role": "system", "content": "You are a concise financial news analyst."},
            {"role": "user", "content": f"Event: {ticker} Alert triggered.\nDetails: {alert_data['msg']}\nPrice: ${price_str} ({change_str}%)\nNews: {news_text}\n\nExplain if news correlates with price."}
        ]

        print(f"  -> Asking AI to explain alert for {ticker}...")
        result = self._call_ai(messages, schema=schema, plugins=[{"id": "web"}])
        
        if result and 'insight' in result:
            return f"**AI Insight:** {result['insight']}"
        return "AI Analysis failed to provide an insight."