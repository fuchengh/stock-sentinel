import requests
import os
import json
import re

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
        if not text: return text
        
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

    def get_analysis(self, ticker, analysis_data, backtest_config=None):
        """
        Sends technical data to LLM for a second opinion.
        """
        if not self.api_key:
            return "AI Analysis skipped (No API Key provided)."

        signal = analysis_data['signal']
        price = analysis_data['price']
        
        # Language instruction
        lang_instruction = "Respond in English."
        analysis_placeholder = "Your analysis text here..."
        
        if self.language in ['zh', 'zh_tw', 'chinese']:
            lang_instruction = "Respond in Traditional Chinese (繁體中文) for the **Analysis** section. **CRITICAL:** Keep the headers (**Verdict**, **Confidence**, **Sizing**) and financial terms (e.g., EMA, RSI, Risk/Reward) in English."
            analysis_placeholder = "你的中文分析..."

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
        You are a senior algorithmic trader. Analyze the trade signal and return a JSON object.
        
        {context_instruction}

        Target: {ticker}
        Current Price: ${price:.2f}
        Signal: {signal}
        Reason: {analysis_data['reason']}
        
        Technical Indicators:
        - EMA 20: ${analysis_data['ema']:.2f}
        - RSI 14: {analysis_data['rsi']:.1f}
        - ATR Stop Loss: ${analysis_data['stop_loss']:.2f}
        
        **Smart Money / Event Context:**
        - Avg Reaction: {analysis_data.get('event_stats', {}).get('avg_reaction', 0):.2f}%
        - Win Rate: {analysis_data.get('event_stats', {}).get('win_rate', 0):.0f}%
        - Insight: {analysis_data.get('event_stats', {}).get('message', 'N/A')}

        Task:
        1. **LANGUAGE:** {lang_instruction}
        2. Evaluate technicals, news, and risk/reward.
        3. Suggest Confidence and Sizing.
        4. **CITATIONS:** You MUST provide the source URL for your claims. Use standard Markdown format: **[Source Name](URL)**. Example: "Revenue is up [Bloomberg](https://...)." Do NOT use bare brackets [1] unless you cannot find a URL.

        Return ONLY a JSON object with this structure:
        {{
            "verdict": "Agree / Disagree / Caution",
            "confidence": "Low / Medium / High",
            "sizing": "Aggressive / Standard / Conservative",
            "analysis": "{analysis_placeholder}"
        }}
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
                {"role": "system", "content": "You are a specialized financial analyst that only outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": { "type": "json_object" }, # Force JSON mode
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        if web_plugin:
            data["plugins"] = web_plugin

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_content = result['choices'][0]['message']['content']
                
                # Clean up XML tags first (in case Grok still sends them)
                cleaned_content = self._clean_text(raw_content)
                
                # Parse JSON and Reconstruct Markdown manually to lock the format
                try:
                    parsed = json.loads(cleaned_content)
                    v = parsed.get('verdict', 'N/A')
                    # Add Emoji to Verdict
                    if 'Agree' in v: v = "✅ " + v
                    elif 'Disagree' in v: v = "❌ " + v
                    elif 'Caution' in v: v = "⚠️ " + v
                    
                    formatted = (
                        f"**Verdict:** {v}\n"
                        f"**Confidence:** {parsed.get('confidence', 'N/A')}\n"
                        f"**Sizing:** {parsed.get('sizing', 'N/A')}\n"
                        f"**Analysis:** {parsed.get('analysis', 'N/A')}"
                    )
                    return formatted
                except:
                    # Fallback: return cleaned raw text if JSON parsing fails
                    return cleaned_content.strip() 
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

        prompt = """
        You are a financial screener.
        1. Use WEB SEARCH to identify 5-8 US stocks with strong momentum or upcoming catalysts.
        2. Focus on liquid, mid-to-large cap stocks.
        3. Return a JSON object with a 'candidates' key containing a list of ticker symbols.
        
        Example: {"candidates": ["NVDA", "AMD", "TSM"]}
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
            "response_format": { "type": "json_object" },
            "plugins": [{"id": "web"}],
            "temperature": 0.5,
            "max_tokens": 200
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
                parsed = json.loads(content)
                return parsed.get('candidates', [])
            return []
                
        except Exception as e:
            print(f"⚠️ AI Candidate Search Exception: {e}")
            return []

    def generate_recommendation_report(self, verified_picks, macro_data=None):
        """
        verified_picks: List of dicts, each containing 'ticker' and 'analysis' (from strategy).
        macro_data: Optional dict from MacroSentinel (regime, reason, etc).
        """
        if not self.api_key or not verified_picks:
            return None
        
        # Prepare data for AI
        picks_summary = []
        for item in verified_picks:
            t = item['ticker']
            a = item['analysis']
            picks_summary.append({
                "ticker": t,
                "price": f"{a['price']:.2f}",
                "signal": a['signal'],
                "rsi": f"{a['rsi']:.1f}",
                "reason": a['reason']
            })
        
        # Macro Context Construction
        macro_context = "Market Context: Unknown (Assume Neutral)"
        if macro_data:
            regime = macro_data.get('regime', 'NEUTRAL')
            reason = macro_data.get('reason', 'N/A')
            tnx = macro_data.get('tnx_current', 0)
            dxy = macro_data.get('dxy_current', 0)
            
            macro_context = (
                f"Regime: {regime}\n"
                f"Reason: {reason}\n"
                f"Yield: {tnx:.2f}%\n"
                f"DXY: {dxy:.2f}"
            )

        lang_name = "Traditional Chinese (繁體中文)" if self.language in ['zh', 'zh_tw', 'chinese'] else "English"

        prompt = f"""
        You are a quantitative analyst. Create a weekly recommendation report.
        
        {macro_context}
        
        Validated Picks (Strategy Results):
        {json.dumps(picks_summary, indent=2)}
        
        Task:
        1. Write a 'market_summary' based on the Macro Regime.
        2. For each pick in the list, write a concise 'analyst_note' combining technicals with recent news.
        3. Use {lang_name} for the summary and notes.

        Return ONLY a JSON object:
        {{
            "market_summary": "...",
            "picks": [
                {{ "ticker": "...", "note": "..." }},
                ...
            ]
        }}
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
                {"role": "system", "content": "You are a financial reporter that only outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": { "type": "json_object" },
            "plugins": [{"id": "web"}],
            "temperature": 0.5,
            "max_tokens": 1000
        }

        try:
            print("  -> Asking AI to summarize verified picks...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                parsed = json.loads(content)
                
                # Reconstruct Markdown in Python to lock headers
                summary_title = "市場機會：" if "Chinese" in lang_name else "Market Opportunity:"
                report = f"**{summary_title}**\n{parsed.get('market_summary', '')}\n\n**🚀 Validated Picks:**\n\n"
                
                # Create a map for quick lookup of the original technical data
                tech_map = {p['ticker']: p for p in picks_summary}
                
                for p in parsed.get('picks', []):
                    ticker = p['ticker']
                    note = p['note']
                    tech = tech_map.get(ticker)
                    
                    if tech:
                        report += f"1. **[{ticker}]** - ${tech['price']}\n"
                        report += f"   - **Strategy:** {tech['signal']} (RSI: {tech['rsi']})\n"
                        report += f"   - **Tech Setup:** {tech['reason']}\n"
                        report += f"   - **Analyst Note:** {note}\n\n"
                
                return report.strip()
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

        price_str = f"{alert_data.get('price', 0):.2f}"
        change_str = f"{alert_data.get('change', 0):.2f}"
        news_text = news_context if news_context else "No recent news found via API."

        prompt = (
            "You are a financial news analyst.\n\n"
            f"Event: {ticker} has triggered an alert.\n"
            "Alert Details:\n"
            f"{alert_data['msg']}\n"
            f"Price: ${price_str} (Change: {change_str}%)\n\n"
            "Recent News Headlines:\n"
            f"{news_text}\n\n"
            "Task:\n"
            "1. Read the alert and the news (if any).\n"
            "2. If news exists, explain if the news explains the price movement.\n"
            "3. If no news, speculate on technical reasons or market sentiment.\n"
            "4. Provide a very short (1-2 sentences) \"Reasoning\" for the user.\n\n"
            "Output Format:\n"
            "**AI Insight:** [Your explanation]"
        )

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
                return self._clean_text(content.strip())
            return None
                
        except Exception as e:
            print(f"⚠️ AI Alert Analysis Exception: {e}")
            return None