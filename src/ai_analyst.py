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
        # Matches <grok:render ...> ... </grok:render>
        # We try to extract the number if it exists, otherwise just remove it.
        
        # Pattern A: Try to find citation_id
        pattern_id = r'<grok:render[^>]*>.*?<argument name="citation_id">\s*(\d+)\s*</argument>.*?</grok:render>'
        text = re.sub(pattern_id, r' [\1] ', text, flags=re.DOTALL)
        
        # Pattern B: Cleanup any remaining grok tags that didn't match Pattern A
        # (e.g. render_media, or different structure)
        pattern_residual = r'<grok:[^>]+>.*?</grok:[^>]+>'
        text = re.sub(pattern_residual, '', text, flags=re.DOTALL)
        
        # Cleanup double spaces created by replacement
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def get_analysis(self, ticker, analysis_data, backtest_config=None):
# ... (inside get_analysis prompt)
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
            macro_context = f"""
            Regime: {macro_data.get('regime', 'NEUTRAL')}
            Reason: {macro_data.get('reason', 'N/A')}
            Yield: {macro_data.get('tnx_current', 0):.2f}%
            DXY: {macro_data.get('dxy_current', 0):.2f}
            """

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

