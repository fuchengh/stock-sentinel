import requests
import os
from datetime import datetime

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = os.getenv('DISCORD_WEBHOOK')
        self.user_id = os.getenv('DISCORD_USER_ID')

    def send_report(self, results):
        """
        results: Dict of {ticker: analysis_dict}
        """
        if not self.webhook_url or not results:
            return

        active_signals = 0

        # Send individual alerts for actionable signals
        for ticker, res in results.items():
            if res.get('type') == 'ALERT':
                 self.send_alert(res)
                 active_signals += 1
                 continue

            if res['signal'] == "HOLD":
                continue 
            
            active_signals += 1
            self._send_single_alert(ticker, res)

        if active_signals == 0:
            print("No active signals today.")

    def send_alert(self, alert_data):
        """
        Send a generic alert (e.g. from Watchdog).
        alert_data: {ticker, color, msg, price, change, ...}
        """
        if not self.webhook_url: return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        embed = {
            "title": f"⚠️ {alert_data['ticker']} Anomaly Detected",
            "description": alert_data['msg'],
            "color": alert_data.get('color', 0xffa500),
            "fields": [
                {"name": "Price", "value": f"${alert_data.get('price', 0):.2f}", "inline": True},
                {"name": "Change", "value": f"{alert_data.get('change', 0):.2f}%", "inline": True},
            ],
            "footer": {"text": f"Stock Sentinel Watchdog • {timestamp}"}
        }
        
        payload = {
            "username": "Sentinel Watchdog 🐕",
            "embeds": [embed]
        }
        
        if self.user_id:
            payload["content"] = f"<@{self.user_id}>"

        try:
            requests.post(self.webhook_url, json=payload)
            print(f"  -> Watchdog alert sent for {alert_data['ticker']}.")
        except Exception as e:
            print(f"Failed to send alert for {alert_data['ticker']}: {e}")
    
    def _send_single_alert(self, ticker, res):
        icon_map = {
            "success": "🟢", "danger": "🔴", "warning": "🟠", "info": "⚪"
        }
        icon = icon_map.get(res['severity'], "⚪")
        
        # Current time for footer
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        footer_text = f"Stock Sentinel • {timestamp}"
        
        if res.get('ai_model'):
            # Clean up model name (e.g. "openai/gpt-4o" -> "gpt-4o") for cleaner display
            model_name = res['ai_model'].split('/')[-1]
            footer_text += f" • AI: {model_name}"

        # Description construction
        desc = f"**Strategy:** Engineer Strategy\n**Reason:** {res['reason']}"
        
        # Add AI Comment if available
        if res.get('ai_comment'):
            desc += f"\n\n**🤖 AI Analyst Verdict:**\n{res['ai_comment']}"

        # Construct Embed
        embed = {
            "title": f"{icon} {ticker} Signal: {res['signal']}",
            "description": desc,
            "color": self._get_color(res['severity']),
            "fields": [
                {"name": "Price", "value": f"${res['price']:.2f}", "inline": True},
                {"name": "EMA 20", "value": f"${res['ema']:.2f}", "inline": True},
                {"name": "RSI", "value": f"{res['rsi']:.1f}", "inline": True},
                {"name": "Stop Loss", "value": f"${res['stop_loss']:.2f}", "inline": True},
            ],
            "footer": {"text": footer_text}
        }

        # If chart exists, attach it
        files = {}
        if res.get('chart'):
            embed["image"] = {"url": f"attachment://{ticker}_chart.png"}
            files = {
                'file': (f"{ticker}_chart.png", res['chart'], 'image/png')
            }
        
        payload = {
            "username": "Stock Sentinel 🤖",
            "avatar_url": "https://i.imgur.com/dJouyw2.jpeg",
            "embeds": [embed]
        }
        
        # Add @mention if user_id is provided
        if self.user_id:
            payload["content"] = f"<@{self.user_id}>"
        
        try:
            # When sending files, payload must be sent as 'payload_json' in multipart/form-data
            # or strictly as json if no files.
            if files:
                requests.post(
                    self.webhook_url, 
                    files=files,
                    data={'payload_json': import_json.dumps(payload)}
                )
            else:
                requests.post(self.webhook_url, json=payload)
                
            print(f"  -> Discord notification sent for {ticker}.")
        except Exception as e:
            print(f"Failed to send Discord notification for {ticker}: {e}")

    def send_recommendations(self, recommendation_text):
        """
        Sends the weekly AI recommendation report.
        """
        if not self.webhook_url or not recommendation_text:
            return

        embed = {
            "title": "🧠 AI Weekly Market Picks",
            "description": recommendation_text,
            "color": 0x9b59b6, # Purple
            "footer": {"text": f"Stock Sentinel AI • {datetime.now().strftime('%Y-%m-%d')}"}
        }
        
        payload = {
            "username": "Sentinel Strategist 🔮",
            "embeds": [embed]
        }
        
        try:
            requests.post(self.webhook_url, json=payload)
            print("  -> AI Recommendations sent to Discord.")
        except Exception as e:
            print(f"Failed to send recommendations: {e}")

    def _get_color(self, severity):
        colors = {
            "success": 0x2ecc71, # Green
            "danger": 0xe74c3c,  # Red
            "warning": 0xf1c40f, # Yellow
            "info": 0x3498db     # Blue
        }
        return colors.get(severity, 0x3498db)

# Helper to avoid global import if possible, or just standard import
import json as import_json