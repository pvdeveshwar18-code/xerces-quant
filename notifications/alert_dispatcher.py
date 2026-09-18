"""
Notification & Signal Alert Dispatcher for Xerces Engine.
Supports Telegram Bot alerts, Discord Webhooks, and Watchlist Entry Point Hit notifications.
"""

import requests
import json
import pandas as pd
from engine.data_loader import fetch_stock_data, calculate_indicators, get_currency_symbol
from engine.decision_engine import evaluate_stock

class AlertDispatcher:
    def __init__(self, telegram_bot_token: str = "", telegram_chat_id: str = "", discord_webhook_url: str = ""):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.discord_webhook_url = discord_webhook_url

    def send_telegram_alert(self, message: str) -> bool:
        """Send notification via Telegram Bot API."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
            r = requests.post(url, json=payload, timeout=5)
            return r.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    def send_discord_alert(self, title: str, description: str, color: int = 65280) -> bool:
        """Send notification via Discord Webhook."""
        if not self.discord_webhook_url:
            return False
        try:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": description,
                    "color": color
                }]
            }
            r = requests.post(self.discord_webhook_url, json=payload, timeout=5)
            return r.status_code in [200, 204]
        except Exception as e:
            print(f"Discord error: {e}")
            return False

    def check_watchlist_entry_hits(self, watchlist: list, timeframe: str = "Swing Trading (1-4 Weeks)") -> list:
        """
        Scans all stocks on the user's Watchlist and detects if current price hits the Entry Zone!
        Returns list of triggered entry alerts.
        """
        triggered_entry_alerts = []
        
        for item in watchlist:
            ticker = item.get("ticker", item.get("symbol", ""))
            name = item.get("name", ticker)
            if not ticker:
                continue
                
            df = fetch_stock_data(ticker, period="6mo", interval="1d")
            if df.empty:
                continue
                
            df = calculate_indicators(df)
            eval_res = evaluate_stock(df, timeframe=timeframe)
            
            curr_price = eval_res["current_price"]
            entry_min = eval_res["entry_min"]
            entry_max = eval_res["entry_max"]
            csym = get_currency_symbol(ticker)
            
            # Check if current price is inside or touching the Entry Zone
            if entry_min <= curr_price <= entry_max * 1.005:
                alert_msg = (
                    f"🎯 **WATCHLIST ENTRY POINT HIT!**\n\n"
                    f"• **Stock**: {name} (`{ticker}`)\n"
                    f"• **Current Price**: {csym}{curr_price:,.2f}\n"
                    f"• **Suggested Entry Zone**: {csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}\n"
                    f"• **Target 1**: {csym}{eval_res['target_1']:,.2f}\n"
                    f"• **Stop Loss**: {csym}{eval_res['stop_loss']:,.2f}\n"
                    f"• **Risk/Reward**: {eval_res['rr_ratio']}x\n"
                    f"• **Signal Confidence**: {eval_res['confidence']}% ({eval_res['decision']})\n"
                )
                
                triggered_entry_alerts.append({
                    "ticker": ticker,
                    "name": name,
                    "current_price": f"{csym}{curr_price:,.2f}",
                    "entry_zone": f"{csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}",
                    "target_1": f"{csym}{eval_res['target_1']:,.2f}",
                    "stop_loss": f"{csym}{eval_res['stop_loss']:,.2f}",
                    "rr_ratio": f"{eval_res['rr_ratio']}x",
                    "decision": eval_res["decision"],
                    "confidence": f"{eval_res['confidence']}%",
                    "alert_msg": alert_msg
                })
                
                # Dispatch alert to external channels if configured
                self.send_telegram_alert(alert_msg)
                self.send_discord_alert(
                    title=f"🎯 ENTRY POINT HIT — {name} ({ticker})",
                    description=f"Price {csym}{curr_price:,.2f} reached Entry Range ({csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}). Target 1: {csym}{eval_res['target_1']:,.2f}",
                    color=65280
                )
                
        return triggered_entry_alerts
