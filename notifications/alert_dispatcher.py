"""
Notification & Signal Alert Dispatcher for Xerces Engine.
Supports Telegram Bot alerts, Discord Webhooks, and Watchlist Entry Point Hit notifications.
"""

import requests
import json
import pandas as pd
from data.loader import load_ohlcv, resolve_ticker
from analytics.indicators import add_indicators
from engine.decision_engine import evaluate_stock

def _get_currency_symbol(ticker: str) -> str:
    if ticker.endswith(".NS") or ticker.endswith(".BO") or not any(x in ticker for x in ["^", "=F"]):
        return "₹"
    return "$"

class AlertDispatcher:
    def __init__(self, telegram_bot_token: str = "", telegram_chat_id: str = "", discord_webhook_url: str = ""):
        # Auto-load saved credentials from SQLite database if not explicitly provided
        if not (telegram_bot_token and telegram_chat_id) and not discord_webhook_url:
            try:
                from data.database import load_notification_config
                cfg = load_notification_config() or {}
                telegram_bot_token = telegram_bot_token or cfg.get("telegram_bot_token", "")
                telegram_chat_id = telegram_chat_id or cfg.get("telegram_chat_id", "")
                discord_webhook_url = discord_webhook_url or cfg.get("discord_webhook_url", "")
            except Exception:
                pass

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

    def test_connections(self) -> dict:
        """Send a test message to configured Telegram and Discord destinations."""
        results = {}
        if self.telegram_bot_token and self.telegram_chat_id:
            results["telegram"] = self.send_telegram_alert("⚡ *XERCES Quant* notification test successful!")
        else:
            results["telegram"] = None

        if self.discord_webhook_url:
            results["discord"] = self.send_discord_alert(
                title="⚡ XERCES Quant Test Notification",
                description="Discord webhook notification channel connected successfully.",
                color=65280
            )
        else:
            results["discord"] = None
        return results

    def dispatch_price_alert(self, alert_dict: dict) -> bool:
        """Dispatch a triggered price or RSI threshold alert to Telegram and Discord."""
        name = alert_dict.get("name", "Asset")
        kind = alert_dict.get("kind", "price").upper()
        op = alert_dict.get("op", ">")
        val = alert_dict.get("value", 0.0)
        curr = alert_dict.get("last_val", 0.0)

        msg = (
            f"🔔 **XERCES QUANT ALERT TRIGGERED**\n\n"
            f"• **Symbol**: {name}\n"
            f"• **Condition**: {kind} {op} {val}\n"
            f"• **Current Value**: {curr:.2f}\n"
        )
        t_ok = self.send_telegram_alert(msg)
        d_ok = self.send_discord_alert(
            title=f"🔔 ALERT TRIGGERED — {name}",
            description=f"{kind} breached condition `{op} {val}` with current value `{curr:.2f}`.",
            color=16753920
        )
        return t_ok or d_ok

    def check_watchlist_entry_hits(self, watchlist: list, timeframe: str = "Swing Trading (1-4 Weeks)") -> list:
        """
        Scans all stocks on the user's Watchlist and detects if current price hits the Entry Zone!
        Returns list of triggered entry alerts with complete numerical trade plan.
        """
        triggered_entry_alerts = []
        
        for item in watchlist:
            ticker = item.get("ticker", item.get("symbol", ""))
            name = item.get("name", ticker)
            if not ticker:
                continue
                
            resolved = resolve_ticker(ticker)
            raw_df = load_ohlcv(resolved, period="6mo")
            if raw_df is None or raw_df.empty or len(raw_df) < 25:
                continue
                
            df = add_indicators(raw_df)
            # Create lowercase compatibility copy for decision engine
            eval_df = df.copy()
            eval_df.columns = [str(c).lower() for c in eval_df.columns]
            eval_res = evaluate_stock(eval_df, timeframe=timeframe)
            
            curr_price = float(eval_res["current_price"])
            entry_min = float(eval_res["entry_min"])
            entry_max = float(eval_res["entry_max"])
            target_1 = float(eval_res["target_1"])
            stop_loss = float(eval_res["stop_loss"])
            csym = _get_currency_symbol(ticker)
            
            # Check if current price is inside or touching the Entry Zone
            if entry_min <= curr_price <= entry_max * 1.005:
                alert_msg = (
                    f"🎯 **WATCHLIST ENTRY POINT HIT!**\n\n"
                    f"• **Stock**: {name} (`{ticker}`)\n"
                    f"• **Current Price**: {csym}{curr_price:,.2f}\n"
                    f"• **Suggested Entry Zone**: {csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}\n"
                    f"• **Target 1**: {csym}{target_1:,.2f}\n"
                    f"• **Stop Loss**: {csym}{stop_loss:,.2f}\n"
                    f"• **Risk/Reward**: {eval_res['rr_ratio']}x\n"
                    f"• **Signal Confidence**: {eval_res['confidence']}% ({eval_res['decision']})\n"
                )
                
                triggered_entry_alerts.append({
                    "ticker": ticker,
                    "name": name,
                    "raw_current_price": curr_price,
                    "raw_entry_min": entry_min,
                    "raw_entry_max": entry_max,
                    "raw_target_1": target_1,
                    "raw_stop_loss": stop_loss,
                    "current_price": f"{csym}{curr_price:,.2f}",
                    "entry_zone": f"{csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}",
                    "target_1": f"{csym}{target_1:,.2f}",
                    "stop_loss": f"{csym}{stop_loss:,.2f}",
                    "rr_ratio": f"{eval_res['rr_ratio']}x",
                    "decision": eval_res["decision"],
                    "confidence": f"{eval_res['confidence']}%",
                    "alert_msg": alert_msg
                })
                
                # Dispatch alert to external channels if configured
                self.send_telegram_alert(alert_msg)
                self.send_discord_alert(
                    title=f"🎯 ENTRY POINT HIT — {name} ({ticker})",
                    description=f"Price {csym}{curr_price:,.2f} reached Entry Range ({csym}{entry_min:,.2f} - {csym}{entry_max:,.2f}). Target 1: {csym}{target_1:,.2f}",
                    color=65280
                )
                
        return triggered_entry_alerts
