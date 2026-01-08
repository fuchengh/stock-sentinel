import requests
import json
import os

def test_recommendation_notif():
    # Hardcoded for testing purposes to bypass dotenv issues in broken environment
    webhook_url = "https://discord.com/api/webhooks/1458359114806595694/VeDceCcB1M_FTIZqw6dFKhBIA62X5l_JrFiYBpVxmxxT-rDHSOGSq5AtrliO60BzNMpa"
    
    test_text = """
**🌍 Market Outlook:** 
市場目前對 AI 基礎設施與網路安全表現出強烈興趣。投資者正轉向「效率」概念股。

**🚀 Validated Picks (Passed Engineer Strategy):**

1. **PLTR (Palantir Technologies)**
   - **Signal:** BUY
   - **Reason:** 突破 EMA 20 且 RSI 位於 52 (回測區間完美)。
   - **Catalyst:** 新的政府合約擴展以及 S&P 500 納入效應。

2. **CRWD (CrowdStrike)**
   - **Signal:** BUY
   - **Reason:** 穩守 ATR 防禦線，儘管板塊波動，趨勢依然完整。
   - **Catalyst:** 企業對 Falcon 平台的需求持續增加。

3. **SMCI (Super Micro Computer)**
   - **Signal:** PROFIT
   - **Reason:** RSI 接近 72。技術面強勢但接近超買區。
   - **Catalyst:** AI 伺服器需求持續供不應求。
"""
    print("Testing Discord Notification for Recommendations...")
    
    embed = {
        "title": "🧠 AI Weekly Market Picks (Python Test)",
        "description": test_text,
        "color": 0x9b59b6, # Purple
        "footer": {"text": "Stock Sentinel AI • 2026-01-07"}
    }
    
    payload = {
        "username": "Sentinel Strategist 🔮",
        "embeds": [embed]
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    # Explicitly encoding to utf-8 bytes to ensure no encoding mess-up by requests (though requests usually handles dicts fine, explicit is safer for debug)
    response = requests.post(webhook_url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers)
    
    if response.status_code in [200, 204]:
        print("✅ Notification sent successfully!")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_recommendation_notif()
