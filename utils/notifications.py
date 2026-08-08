"""
XERCES Real-Time Webhook & Telegram Alert Dispatcher
Sends automated push notifications to Telegram Bot API, Discord/Slack Webhooks, or custom HTTP endpoints
when price thresholds, RSI levels, ML Buy Signals, or Bollinger Squeezes trigger.
"""

import json
import urllib.request
import urllib.parse
import streamlit as st

class AlertNotificationDispatcher:
    """
    Real-Time Push Notification Engine for Telegram & Webhooks.
    """

    @staticmethod
    def send_telegram(bot_token: str, chat_id: str, title: str, text_body: str) -> dict:
        """
        Sends formatted message to Telegram Chat via Bot API.
        """
        if not bot_token or not chat_id:
            return {"success": False, "error": "Missing Telegram Bot Token or Chat ID."}

        formatted_msg = f"<b>{title}</b>\n\n{text_body}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": formatted_msg,
            "parse_mode": "HTML"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("ok"):
                    return {"success": True, "error": None}
                return {"success": False, "error": res_data.get("description", "Unknown Telegram API error")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_webhook(webhook_url: str, title: str, payload_dict: dict) -> dict:
        """
        Posts JSON payload to generic HTTP Webhook (Discord, Slack, Zapier, Make, custom servers).
        """
        if not webhook_url:
            return {"success": False, "error": "Missing Webhook URL."}

        # Check if Discord Webhook format
        if "discord.com/api/webhooks" in webhook_url:
            post_body = {
                "embeds": [{
                    "title": title,
                    "description": payload_dict.get("message", ""),
                    "color": 581478, # Cyan
                    "fields": [
                        {"name": k, "value": str(v), "inline": True}
                        for k, v in payload_dict.items() if k != "message"
                    ]
                }]
            }
        else:
            post_body = {
                "title": title,
                "data": payload_dict
            }

        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(post_body).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "XERCES-Quant-Engine/1.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def dispatch_alert(
        cls,
        alert_title: str,
        alert_details: dict,
        telegram_token: str = "",
        telegram_chat_id: str = "",
        webhook_url: str = ""
    ) -> dict:
        """
        Dispatches alert notification to all configured channels.
        """
        msg_lines = [
            f"⚡ <b>Stock:</b> {alert_details.get('name', 'N/A')} ({alert_details.get('ticker', '')})",
            f"💵 <b>Price:</b> ₹{alert_details.get('price', 0.0):,.2f}",
            f"📊 <b>RSI:</b> {alert_details.get('rsi', 0.0):.1f}",
            f"🤖 <b>ML Signal:</b> {alert_details.get('ml_signal', 'HOLD')} ({alert_details.get('confidence', 50)}%)",
            f"📝 <b>Condition:</b> {alert_details.get('condition_desc', '')}"
        ]
        msg_text = "\n".join(msg_lines)

        results = {}
        if telegram_token and telegram_chat_id:
            results["telegram"] = cls.send_telegram(telegram_token, telegram_chat_id, alert_title, msg_text)
        
        if webhook_url:
            results["webhook"] = cls.send_webhook(webhook_url, alert_title, {
                "message": msg_text.replace("<b>", "").replace("</b>", ""),
                **alert_details
            })

        return results
